import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'recipes.sample.json'

ALLERGEN_KEYWORDS = [
    'noix', 'noix de', 'amande', 'amandes', 'arachide', 'arachides', 'cacahuete', 'cacahuètes',
    'lait', 'fromage', 'beurre', 'oeuf', 'oeufs', 'gluten', 'farine', 'blé', 'froment',
    'tomate',
    'crevette', 'crevettes', 'poisson', 'crustacé', 'mollusque', 'soja', 'tofu', 'sésame', 'sesame'
]


def find_allergens_in_recipe(recipe, keywords):
    """Return list of matched keywords using word-boundary regex to avoid substring false-positives."""
    matches = set()
    for ing in recipe.get('ingredients', []):
        name = ''
        if isinstance(ing, dict):
            name = ing.get('name', '')
        else:
            name = str(ing)
        for k in keywords:
            # use word boundary matching, case-insensitive
            pattern = r"\b" + re.escape(k.lower()) + r"\b"
            if re.search(pattern, name.lower()):
                matches.add(k)
    return sorted(matches)


def main():
    recipes = json.loads(DATA.read_text(encoding='utf-8'))
    results = []
    for r in recipes:
        found = find_allergens_in_recipe(r, ALLERGEN_KEYWORDS)
        if found:
            results.append((r.get('id', r.get('name')), r.get('name'), found))
    if not results:
        print('Aucune recette contenant les allergènes listés n\'a été trouvée.')
        return
    print('Recettes contenant des allergènes (keyword matched):')
    for rid, name, found in results:
        print(f'- {rid}: {name} -> {", ".join(found)}')

if __name__ == "__main__":
    main()
