"""Fuzzy ingredient matching for Grocy integration."""

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from beersmith_mcp.models import IngredientMatch
from beersmith_mcp.parser import BeerSmithParser


@dataclass
class MatchCandidate:
    """Internal matching candidate."""

    name: str
    ingredient_type: str  # 'hop', 'grain', 'yeast', 'misc'
    beersmith_id: str
    keywords: list[str]


class IngredientMatcher:
    """Fuzzy matcher for ingredient names."""

    def __init__(self, parser: BeerSmithParser):
        """Initialize with a BeerSmith parser."""
        self.parser = parser
        self._candidates: list[MatchCandidate] | None = None

    def _build_candidates(self) -> list[MatchCandidate]:
        """Build the list of match candidates from BeerSmith data."""
        candidates = []

        # Add hops
        for hop in self.parser.get_hops():
            keywords = self._extract_keywords(hop.name)
            # Add origin as keyword
            if hop.origin:
                keywords.extend(self._extract_keywords(hop.origin))
            candidates.append(
                MatchCandidate(
                    name=hop.name,
                    ingredient_type="hop",
                    beersmith_id=hop.id,
                    keywords=keywords,
                )
            )

        # Add grains
        for grain in self.parser.get_grains():
            keywords = self._extract_keywords(grain.name)
            if grain.origin:
                keywords.extend(self._extract_keywords(grain.origin))
            if grain.supplier:
                keywords.extend(self._extract_keywords(grain.supplier))
            candidates.append(
                MatchCandidate(
                    name=grain.name,
                    ingredient_type="grain",
                    beersmith_id=grain.id,
                    keywords=keywords,
                )
            )

        # Add yeasts
        for yeast in self.parser.get_yeasts():
            keywords = self._extract_keywords(yeast.name)
            keywords.append(yeast.product_id.lower())
            if yeast.lab:
                keywords.extend(self._extract_keywords(yeast.lab))
            candidates.append(
                MatchCandidate(
                    name=yeast.name,
                    ingredient_type="yeast",
                    beersmith_id=yeast.id,
                    keywords=keywords,
                )
            )

        # Add misc
        for misc in self.parser.get_misc_ingredients():
            keywords = self._extract_keywords(misc.name)
            candidates.append(
                MatchCandidate(
                    name=misc.name,
                    ingredient_type="misc",
                    beersmith_id=misc.id,
                    keywords=keywords,
                )
            )

        return candidates

    @property
    def candidates(self) -> list[MatchCandidate]:
        """Get or build the candidates list."""
        if self._candidates is None:
            self._candidates = self._build_candidates()
        return self._candidates

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from a string."""
        # Remove common suffixes and split
        text = text.lower()
        # Remove parenthetical content
        text = re.sub(r'\([^)]*\)', '', text)
        # Remove common brewing terms that don't help matching
        stop_words = {'malt', 'malted', 'hops', 'hop', 'yeast', 'grain', 'extract', 'liquid', 'dry'}
        words = re.findall(r'\b[a-z]+\b', text)
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        name = name.lower()
        # Remove year/vintage (e.g., "2023")
        name = re.sub(r'\b20\d{2}\b', '', name)
        # Remove common suffixes
        name = re.sub(r'\s+(hops?|malt|grain|yeast|pellets?|leaf)\s*$', '', name)
        # Remove parenthetical content
        name = re.sub(r'\([^)]*\)', '', name)
        # Normalize whitespace
        name = ' '.join(name.split())
        return name.strip()

    def match_ingredient(
        self,
        query: str,
        ingredient_types: list[str] | None = None,
        threshold: float = 0.5,
        limit: int = 5,
    ) -> list[IngredientMatch]:
        """
        Match a query string to BeerSmith ingredients.

        Args:
            query: The ingredient name to match (e.g., from Grocy)
            ingredient_types: Optional filter for types ('hop', 'grain', 'yeast', 'misc')
            threshold: Minimum confidence score (0.0 to 1.0)
            limit: Maximum number of matches to return

        Returns:
            List of IngredientMatch objects sorted by confidence
        """
        matches = []
        query_normalized = self._normalize_name(query)
        query_keywords = self._extract_keywords(query)

        # Filter candidates by type if specified
        candidates = self.candidates
        if ingredient_types:
            candidates = [c for c in candidates if c.ingredient_type in ingredient_types]

        for candidate in candidates:
            # Calculate various similarity scores
            scores = []

            # 1. Exact match (after normalization)
            candidate_normalized = self._normalize_name(candidate.name)
            if query_normalized == candidate_normalized:
                scores.append(1.0)

            # 2. Fuzzy ratio on full names
            ratio = fuzz.ratio(query_normalized, candidate_normalized) / 100.0
            scores.append(ratio * 0.8)

            # 3. Token set ratio (handles word reordering)
            token_ratio = fuzz.token_set_ratio(query_normalized, candidate_normalized) / 100.0
            scores.append(token_ratio * 0.9)

            # 4. Partial ratio (handles substrings)
            partial_ratio = fuzz.partial_ratio(query_normalized, candidate_normalized) / 100.0
            scores.append(partial_ratio * 0.7)

            # 5. Keyword matching
            if query_keywords and candidate.keywords:
                keyword_matches = sum(1 for kw in query_keywords if kw in candidate.keywords)
                keyword_score = keyword_matches / max(len(query_keywords), 1)
                scores.append(keyword_score * 0.85)

            # Take the best score
            best_score = max(scores) if scores else 0.0

            if best_score >= threshold:
                matches.append(
                    IngredientMatch(
                        query=query,
                        matched_name=candidate.name,
                        matched_type=candidate.ingredient_type,
                        confidence=round(best_score, 3),
                        beersmith_id=candidate.beersmith_id,
                    )
                )

        # Sort by confidence and limit
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[:limit]

    def match_ingredients_batch(
        self,
        queries: list[str],
        ingredient_types: list[str] | None = None,
        threshold: float = 0.5,
    ) -> dict[str, list[IngredientMatch]]:
        """
        Match multiple ingredient names to BeerSmith ingredients.

        Args:
            queries: List of ingredient names to match
            ingredient_types: Optional filter for types
            threshold: Minimum confidence score

        Returns:
            Dictionary mapping each query to its matches
        """
        results = {}
        for query in queries:
            results[query] = self.match_ingredient(
                query, ingredient_types=ingredient_types, threshold=threshold
            )
        return results

    def suggest_substitutes(self, ingredient_name: str, ingredient_type: str) -> list[str]:
        """
        Suggest substitutes for an ingredient.

        This uses a simple heuristic based on similar names and types.
        For hops, we could enhance this with actual substitution data.
        """
        substitutes = []

        # Get the original ingredient
        matches = self.match_ingredient(
            ingredient_name, ingredient_types=[ingredient_type], threshold=0.9, limit=1
        )
        if not matches:
            return substitutes

        original = matches[0].matched_name

        # Find similar ingredients
        similar = self.match_ingredient(
            ingredient_name, ingredient_types=[ingredient_type], threshold=0.4, limit=10
        )

        # Return similar items excluding the original
        for match in similar:
            if match.matched_name != original:
                substitutes.append(match.matched_name)

        return substitutes[:5]


# Common hop substitution data (could be expanded)
HOP_SUBSTITUTES = {
    "cascade": ["centennial", "amarillo", "simcoe"],
    "centennial": ["cascade", "chinook", "columbus"],
    "citra": ["galaxy", "mosaic", "simcoe"],
    "mosaic": ["citra", "galaxy", "amarillo"],
    "simcoe": ["amarillo", "summit", "warrior"],
    "amarillo": ["cascade", "centennial", "citra"],
    "chinook": ["columbus", "centennial", "nugget"],
    "columbus": ["chinook", "centennial", "tomahawk"],
    "galaxy": ["citra", "mosaic", "nelson sauvin"],
    "hallertau": ["liberty", "mt. hood", "crystal"],
    "saaz": ["sterling", "ultra", "tettnang"],
    "fuggle": ["willamette", "styrian goldings", "east kent goldings"],
    "east kent goldings": ["fuggle", "progress", "styrian goldings"],
    "magnum": ["horizon", "german magnum", "warrior"],
    "warrior": ["magnum", "millennium", "nugget"],
}


def get_hop_substitutes(hop_name: str) -> list[str]:
    """Get known substitutes for a hop variety."""
    hop_lower = hop_name.lower()
    for key, subs in HOP_SUBSTITUTES.items():
        if key in hop_lower or hop_lower in key:
            return subs
    return []
