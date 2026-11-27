#!/usr/bin/env python3
"""Add a recipe to the shared Roku, Fire TV, and browser cookbook."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

import build_data


def ask(label, default=None, optional=False):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        answer = input(f"{label}{suffix}: ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        if optional:
            return ""


def number(label, default, low, high):
    while True:
        answer = ask(label, str(default))
        if answer.isdecimal() and low <= int(answer) <= high:
            return int(answer)
        print(f"Enter a whole number from {low} to {high}.")


def recipe_id(title):
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")


def collect(categories):
    title = ask("Recipe title")
    print("Categories")
    for index, category in enumerate(categories, start=1):
        print(f"  {index}. {category}")
    category = categories[number("Category number", 1, 1, len(categories)) - 1]
    cuisine = ask("Cuisine", "Family")
    description = ask("Short description")
    prep = number("Prep minutes", 15, 1, 600)
    cook = number("Cook minutes", 30, 0, 720)
    serves = number("Servings", 4, 1, build_data.MAX_SERVINGS)
    note = ask("Kitchen note (optional)", optional=True)
    tools = ask("Cookware, separated by commas (optional)", optional=True)
    cookware = [item.strip() for item in tools.split(",") if item.strip()]

    print("\nEnter one ingredient per line. Leave a line blank to finish.")
    ingredients = []
    while item := ask(f"Ingredient {len(ingredients) + 1}", optional=True):
        ingredients.append(item)

    print("\nEnter one direction per line. You can add a heading with 'Heading | Direction'.")
    print("Write times as '10 minutes' to get a cook-mode timer. Leave a line blank to finish.")
    steps = []
    while line := ask(f"Direction {len(steps) + 1}", optional=True):
        head, divider, text = line.partition("|")
        steps.append({"lead": head.strip() if divider else f"Step {len(steps) + 1}",
                      "text": text.strip() if divider else line})

    return {
        "id": recipe_id(title),
        "title": title,
        "category": category,
        "cuisine": cuisine,
        "description": description,
        "prepMin": prep,
        "cookMin": cook,
        "serves": serves,
        "difficulty": "Easy",
        "cookware": cookware,
        "ingredients": ingredients,
        "steps": steps,
        "kitchenNote": note,
        "accent": {"garnish": "herbs", "color": "#8B9D61"},
        "image": build_data.SHARED_DISH_IMAGE,
        "photo": "images/photos/farmhouse.png",
        "tags": [],
    }


def append_recipe(source, document, recipe):
    """Keep the rest of the recipe file byte-for-byte when the recipes list is last."""
    end = source.rfind("]")
    if document["recipes"] and re.fullmatch(r"\s*}\s*", source[end + 1:]) and list(document)[-1] == "recipes":
        entry = json.dumps(recipe, ensure_ascii=False, indent=2)
        entry = "\n".join("    " + line for line in entry.splitlines())
        return source[:end].rstrip() + ",\n" + entry + "\n  " + source[end:]
    document["recipes"].append(recipe)
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate the recipe without saving it.")
    args = parser.parse_args()
    path = Path(build_data.DATA)
    source = path.read_text(encoding="utf-8")
    document = json.loads(source)
    layout = json.loads(Path(build_data.LAYOUT).read_text(encoding="utf-8"))
    try:
        recipe = collect(document["categories"])
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nRecipe entry cancelled.\n")

    updated = append_recipe(source, document, recipe)
    build_data.validate(json.loads(updated), layout)
    if build_data.errors:
        parser.exit(1, "\n".join(build_data.errors) + "\n")
    if not all(step["lead"] and step["text"] for step in recipe["steps"]):
        parser.exit(1, "Every direction needs a heading and text.\n")
    if args.dry_run:
        print(f"Recipe is valid: {recipe['title']}")
        return

    # Write beside the source so replacement is atomic even on a separate filesystem.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as out:
        temporary = Path(out.name)
        try:
            out.write(updated)
            out.close()
            temporary.chmod(path.stat().st_mode & 0o777)
            if path.read_text(encoding="utf-8") != source:
                parser.exit(1, "The recipe file changed during entry. Run the wizard again.\n")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    build_data.main()
    print(f"Added {recipe['title']}. Open web/index.html to view it.")


if __name__ == "__main__":
    main()
