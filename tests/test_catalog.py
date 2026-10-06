import re

import pytest

from conftest import REPO, write
from mayhem.catalog import Catalog, CatalogError, load_pins


def catalog(tmp_path, modules: dict[str, str], profiles: dict[str, str] | None = None, root_name="root"):
    root = tmp_path / root_name
    for name, toml in modules.items():
        write(root / "modules" / name / "module.toml", toml)
    for name, toml in (profiles or {}).items():
        write(root / "profiles" / f"{name}.toml", toml)
    return root


def names(modules):
    return [m.name for m in modules]


def test_requirements_come_first_in_stable_order(tmp_path):
    root = catalog(tmp_path, {
        "a": 'requires = ["c", "b"]',
        "b": 'requires = ["c"]',
        "c": "",
        "d": "",
    })
    cat = Catalog.load([root])
    assert names(cat.plan(["d", "a"], "linux")) == ["d", "c", "b", "a"]


def test_cycle_is_reported_with_its_path(tmp_path):
    root = catalog(tmp_path, {"a": 'requires = ["b"]', "b": 'requires = ["a"]'})
    with pytest.raises(CatalogError, match="a -> b -> a"):
        Catalog.load([root]).plan(["a"], "linux")


def test_missing_requirement_names_who_needs_it(tmp_path):
    root = catalog(tmp_path, {"a": 'requires = ["ghost"]'})
    with pytest.raises(CatalogError, match="'ghost' \\(required by a\\)"):
        Catalog.load([root]).plan(["a"], "linux")


def test_module_for_other_os_is_dropped_unless_required(tmp_path):
    root = catalog(tmp_path, {
        "winonly": 'os = ["windows"]',
        "needs-win": 'requires = ["winonly"]',
        "plain": "",
    })
    cat = Catalog.load([root])
    assert names(cat.plan(["winonly", "plain"], "linux")) == ["plain"]
    with pytest.raises(CatalogError, match="doesn't support linux"):
        cat.plan(["needs-win"], "linux")


def test_skip_leaves_module_out_but_keeps_order(tmp_path):
    root = catalog(tmp_path, {"a": 'requires = ["b"]', "b": ""})
    assert names(Catalog.load([root]).plan(["a"], "linux", skip={"b"})) == ["a"]


def test_profile_includes_expand_once(tmp_path):
    root = catalog(tmp_path, {"a": "", "b": ""}, {
        "base": 'modules = ["a"]',
        "human": 'include = ["base"]\nmodules = ["b", "a"]',
    })
    assert Catalog.load([root]).profile_modules(["human", "base"]) == ["a", "b"]


def test_profile_include_cycle_and_unknown_profile(tmp_path):
    root = catalog(tmp_path, {}, {"x": 'include = ["y"]', "y": 'include = ["x"]'})
    cat = Catalog.load([root])
    with pytest.raises(CatalogError, match="x -> y -> x"):
        cat.profile_modules(["x"])
    with pytest.raises(CatalogError, match="unknown profile 'nope'"):
        cat.profile_modules(["nope"])


def test_later_root_layers_over_earlier(tmp_path):
    public = catalog(tmp_path, {"a": 'description = "public"'}, root_name="public")
    fleet = catalog(tmp_path, {"a": 'description = "fleet"'}, root_name="fleet")
    write(public / "versions.toml", 'a = "1.0"\nb = "2.0"\n')
    write(fleet / "versions.toml", 'a = "1.1"\n')
    cat = Catalog.load([public, fleet])
    assert cat.modules["a"].description == "fleet"
    assert cat.pins == {"a": "1.1", "b": "2.0"}


def test_lib_dirs_are_not_modules(tmp_path):
    root = catalog(tmp_path, {"_lib": "", "real": ""})
    assert list(Catalog.load([root]).modules) == ["real"]


def test_non_string_pin_is_rejected(tmp_path):
    with pytest.raises(CatalogError, match="must be strings: a"):
        load_pins(write(tmp_path / "versions.toml", "a = 1\n"))


def test_bad_toml_names_the_file(tmp_path):
    root = catalog(tmp_path, {"a": "requires = ["})
    with pytest.raises(CatalogError, match="module.toml"):
        Catalog.load([root])


def test_repo_catalog_is_complete():
    cat = Catalog.load([REPO])
    for os_name in ("windows", "linux"):
        for module in cat.plan(cat.profile_modules(list(cat.profiles)), os_name):
            for verb in ("check", "install"):
                assert module.script(verb, os_name).is_file(), f"{module.name} has no {verb} for {os_name}"


def test_every_pin_is_annotated_and_has_a_module():
    lines = (REPO / "versions.toml").read_text(encoding="utf-8").splitlines()
    cat = Catalog.load([REPO])
    for i, line in enumerate(lines):
        if m := re.match(r"^([\w-]+)\s*=", line):
            assert re.match(r"#\s*(renovate|floor):", lines[i - 1]), f"pin {m[1]} has no renovate/floor comment"
            assert m[1] in cat.modules, f"pin {m[1]} has no module"
