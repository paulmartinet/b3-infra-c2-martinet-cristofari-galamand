from typing import Any, Dict, List, Tuple
import math
import random


def is_vege(recipe: Dict[str, Any]) -> bool:
    return "tags" in recipe and any(t.lower() == "vege" for t in recipe["tags"])


def fits_time(recipe: Dict[str, Any], max_time: int | None) -> bool:
    if max_time is None:
        return True
    return int(recipe.get("time_min", 9999)) <= max_time


def has_excluded_ingredients(recipe: Dict[str, Any], exclude_ingredients: List[str] | None) -> bool:
    """Return True if recipe contains any of the exclude_ingredients.

    The function is robust to ingredient entries being either dicts with a "name"
    key (the standard format) or plain strings (older/other formats).
    Matching is case-insensitive and checks membership (substring) to be flexible.
    """
    if not exclude_ingredients:
        return False
    recipe_ingredients = recipe.get("ingredients", [])
    for excl in exclude_ingredients:
        low_excl = excl.lower()
        for ingredient in recipe_ingredients:
            name = ingredient.get("name", "") if isinstance(ingredient, dict) else str(ingredient)
            if low_excl in name.lower():
                return True
    return False


def within_budget_avg(selected: List[Dict[str, Any]], avg_target: float, tolerance: float = 0.2) -> bool:
    if not selected:
        return True
    cur_avg = sum(float(r.get("budget_eur", 0.0)) for r in selected) / len(selected)
    return (avg_target * (1 - tolerance)) <= cur_avg <= (avg_target * (1 + tolerance))


def select_menu(
    recipes: List[Dict[str, Any]],
    days: int = 7,
    min_vege: int = 2,
    max_time: int | None = None,
    avg_budget: float | None = None,
    tolerance: float = 0.2,
    seed: int | None = 42,
    no_duplicates: bool = False,
    exclude_ingredients: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Sélection simple et déterministe (via seed) :
    - Filtre par temps et par ingrédients exclus (si fournis).
    - Tire au sort jusqu'à avoir 'days' recettes.
    - Si no_duplicates=True, évite les doublons exacts quand c'est possible.
    - Vérifie min_vege et budget moyen (si fourni). Réessaie quelques fois.
    """
    pool = [r for r in recipes if fits_time(r, max_time) and not has_excluded_ingredients(r, exclude_ingredients)]
    if seed is not None:
        random.seed(seed)
    attempts = 200
    best: List[Dict[str, Any]] = []
    for _ in range(attempts):
        if no_duplicates and len(pool) >= days:
            # Si on a assez de recettes, on tire sans remise pour éviter les doublons
            cand = random.sample(pool, k=days)
        else:
            # Sinon, on permet les doublons (soit no_duplicates=False, soit pas assez de recettes)
            cand = random.sample(pool, k=min(days, len(pool))) if len(pool) >= days else pool[:]
            # Si pas assez, on complète en re-piochant (permet petit dataset)
            while len(cand) < days and pool:
                cand.append(random.choice(pool))
        # Contraintes
        vege_count = sum(1 for r in cand if is_vege(r))
        if vege_count < min_vege:
            continue
        if avg_budget is not None and not within_budget_avg(cand, avg_budget, tolerance):
            continue
        best = cand
        break
    if not best:
        # Dernier recours: prendre les premiers qui passent le temps
        best = pool[:days] if len(pool) >= days else (pool + pool)[:days]
    return best


def consolidate_shopping_list(menu: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrège par (name, unit). Ne gère pas la conversion d’unités (simple au départ).
    """
    agg: Dict[Tuple[str, str], float] = {}
    for r in menu:
        for ing in r.get("ingredients", []):
            # ing expected to be dict with name, qty, unit
            name = ing.get("name") if isinstance(ing, dict) else str(ing)
            unit = ing.get("unit", "") if isinstance(ing, dict) else ""
            qty = float(ing.get("qty", 0.0)) if isinstance(ing, dict) else 0.0
            key = (name.strip().lower(), unit.strip().lower())
            agg[key] = agg.get(key, 0.0) + qty
    items = [
        {"name": name, "qty": round(qty, 2), "unit": unit}
        for (name, unit), qty in sorted(agg.items())
    ]
    return items


def plan_menu(
    recipes: List[Dict[str, Any]],
    days: int = 7,
    min_vege: int = 2,
    max_time: int | None = None,
    avg_budget: float | None = None,
    tolerance: float = 0.2,
    seed: int | None = 42,
    no_duplicates: bool = False,
    exclude_ingredients: List[str] | None = None,
    min_fish: int = 0,
    max_meat: int | None = None,
) -> Dict[str, Any]:
    menu = select_menu(
        recipes, days=days, min_vege=min_vege, max_time=max_time,
        avg_budget=avg_budget, tolerance=tolerance, seed=seed,
        no_duplicates=no_duplicates,
        exclude_ingredients=exclude_ingredients
    )
    shopping = consolidate_shopping_list(menu)
    result = {"days": days, "menu": menu, "shopping_list": shopping}

    # Ajouter un warning si no_duplicates demandé mais impossible
    if no_duplicates:
        unique_recipes = {r.get("id", r.get("name")) for r in menu}  # utilise name si pas d'id
        if len(unique_recipes) < days:
            result.setdefault("warnings", []).append(
                "no_duplicates demandé mais pas assez de recettes uniques disponibles"
            )
    return result
