"""Spreadsheets, data & analytics tools.

Pure-Python formula evaluation and data manipulation over in-memory
tables (list-of-dicts). No pandas required. Designed to work on iSH.
"""
from __future__ import annotations

import ast
import csv as _csv
import io as _io
import math
import operator as op
import re
import statistics
from typing import Any

_SAFE_BINOPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow}
_SAFE_UNARYOPS = {ast.UAdd: op.pos, ast.USub: op.neg}

_FUNCS = {
    "sum": sum, "min": min, "max": max, "avg": lambda x: sum(x) / len(x) if x else 0,
    "mean": statistics.mean, "median": statistics.median, "mode": statistics.mode,
    "stdev": statistics.stdev, "pstdev": statistics.pstdev, "variance": statistics.variance,
    "sqrt": math.sqrt, "abs": abs, "round": round, "len": len,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log, "log10": math.log10,
    "exp": math.exp, "ceil": math.ceil, "floor": math.floor,
}


def _is_num(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _eval_node(node, ctx):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return ctx.get(node.id, 0)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
        return _SAFE_BINOPS[type(node.op)](_eval_node(node.left, ctx), _eval_node(node.right, ctx))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARYOPS:
        return _SAFE_UNARYOPS[type(node.op)](_eval_node(node.operand, ctx))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        args = [_eval_node(a, ctx) for a in node.args]
        if node.func.id in ("sum", "min", "max", "avg"):
            return _FUNCS[node.func.id](args)
        return _FUNCS[node.func.id](args[0])
    if isinstance(node, ast.List):
        return [_eval_node(e, ctx) for e in node.elts]
    raise ValueError(f"unsafe expression: {ast.dump(node)}")


def _eval_formula(expr: str, ctx: dict) -> Any:
    return _eval_node(ast.parse(expr, mode="eval"), ctx)


def _col_index(ref: str) -> int:
    ref = re.match(r"[A-Z]+", ref.upper()).group(0)
    n = 0
    for ch in ref:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _cell_ref(grid: list[list], ref: str):
    m = re.match(r"([A-Z]+)(\d+)", ref.upper())
    if not m:
        return None
    col, row = _col_index(m.group(1)), int(m.group(2)) - 1
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        return grid[row][col]
    return None


def _filter_rows(rows, column, oper, value):
    ops = {"eq": lambda a, b: a == b, "ne": lambda a, b: a != b, "gt": lambda a, b: a > b, "lt": lambda a, b: a < b, "ge": lambda a, b: a >= b, "le": lambda a, b: a <= b, "contains": lambda a, b: str(b) in str(a)}
    f = ops.get(oper, ops["eq"])
    return [r for r in rows if str(r.get(column, "")) != "" and f(r.get(column), value)]


def _sort_rows(rows, by, descending=False):
    return sorted(rows, key=lambda r: r.get(by, ""), reverse=descending)


def _group_aggregate(rows, by, agg, value_col):
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(str(r.get(by, "")), []).append(r.get(value_col, 0))
    out = []
    for k, vals in groups.items():
        nums = [float(v) for v in vals if _is_num(v)]
        if agg == "sum":
            v = sum(nums)
        elif agg == "avg":
            v = sum(nums) / len(nums) if nums else 0
        elif agg == "count":
            v = len(vals)
        elif agg == "min":
            v = min(nums) if nums else 0
        elif agg == "max":
            v = max(nums) if nums else 0
        else:
            v = len(vals)
        out.append({by: k, agg: round(v, 4) if isinstance(v, float) else v})
    return out


def _pivot(rows, rows_field, cols_field, value_field, agg="sum"):
    pivot: dict[str, dict[str, float]] = {}
    col_keys: set[str] = set()
    for r in rows:
        rk, ck = str(r.get(rows_field, "")), str(r.get(cols_field, ""))
        col_keys.add(ck)
        val = r.get(value_field, 0)
        val = float(val) if _is_num(val) else 0
        pivot.setdefault(rk, {}).setdefault(ck, 0)
        if agg == "sum":
            pivot[rk][ck] += val
        elif agg == "count":
            pivot[rk][ck] += 1
        elif agg == "max":
            pivot[rk][ck] = max(pivot[rk][ck], val)
        elif agg == "min":
            pivot[rk][ck] = min(pivot[rk][ck], val)
    return {"columns": sorted(col_keys), "rows": pivot}


def _describe(values):
    if not values:
        return {"error": "no values"}
    return {
        "count": len(values), "sum": round(sum(values), 4),
        "mean": round(statistics.mean(values), 4), "median": round(statistics.median(values), 4),
        "min": min(values), "max": max(values), "range": max(values) - min(values),
        "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0,
        "variance": round(statistics.variance(values), 4) if len(values) > 1 else 0,
    }


def _moving_average(values, window):
    if window <= 0 or not values:
        return []
    return [round(sum(values[i:i + window]) / window, 4) for i in range(len(values) - window + 1)]


def _linear_regression(xs, ys):
    n = len(xs)
    if n < 2 or n != len(ys):
        return {"error": "need equal-length xs and ys with at least 2 points"}
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs) or 1
    slope = num / den
    intercept = mean_y - slope * mean_x
    r = num / (math.sqrt(sum((x - mean_x) ** 2 for x in xs)) * math.sqrt(sum((y - mean_y) ** 2 for y in ys)) or 1)
    return {"slope": round(slope, 6), "intercept": round(intercept, 6), "r": round(r, 6), "r_squared": round(r * r, 6)}


def _csv_parse(text, delimiter=","):
    return list(_csv.DictReader(_io.StringIO(text), delimiter=delimiter))


TOOLS: list[dict] = [
    {"name": "data_eval_formula", "description": "Evaluate a spreadsheet-style formula (e.g. sum([a,b,c]), a*b+2) with a context of named variables. Safe AST evaluation — no builtins, no attributes.", "params": {"formula": "string", "context": "object"}, "run": lambda a: {"result": _eval_formula(a.get("formula", ""), a.get("context", {}))}},
    {"name": "data_cell_lookup", "description": "Look up a value in a 2D grid (list of lists) by A1-style cell reference (e.g. B3).", "params": {"grid": "list", "ref": "string"}, "run": lambda a: {"value": _cell_ref(a.get("grid", []), a.get("ref", ""))}},
    {"name": "data_filter_rows", "description": "Filter rows of a list-of-dicts by a column with an operator (eq, ne, gt, lt, ge, le, contains) and value.", "params": {"rows": "list", "column": "string", "op": "string", "value": "any"}, "run": lambda a: {"rows": _filter_rows(a.get("rows", []), a.get("column", ""), a.get("op", "eq"), a.get("value"))}},
    {"name": "data_sort_rows", "description": "Sort a list-of-dicts by a column, ascending or descending.", "params": {"rows": "list", "by": "string", "descending": "bool"}, "run": lambda a: {"rows": _sort_rows(a.get("rows", []), a.get("by", ""), bool(a.get("descending", False)))}},
    {"name": "data_group_aggregate", "description": "Group rows by a column and aggregate a value column (sum, avg, count, min, max).", "params": {"rows": "list", "by": "string", "agg": "string", "value_col": "string"}, "run": lambda a: {"groups": _group_aggregate(a.get("rows", []), a.get("by", ""), a.get("agg", "count"), a.get("value_col", ""))}},
    {"name": "data_pivot", "description": "Build a pivot table from rows: rows_field, cols_field, value_field, and aggregation (sum, count, min, max).", "params": {"rows": "list", "rows_field": "string", "cols_field": "string", "value_field": "string", "agg": "string"}, "run": lambda a: _pivot(a.get("rows", []), a.get("rows_field", ""), a.get("cols_field", ""), a.get("value_field", ""), a.get("agg", "sum"))},
    {"name": "data_describe", "description": "Compute descriptive statistics (count, sum, mean, median, min, max, range, stdev, variance) for a list of numbers.", "params": {"values": "list"}, "run": lambda a: _describe([float(v) for v in a.get("values", []) if _is_num(v)])},
    {"name": "data_moving_average", "description": "Compute a simple moving average over a numeric series with a given window size.", "params": {"values": "list", "window": "int"}, "run": lambda a: {"ma": _moving_average([float(v) for v in a.get("values", []) if _is_num(v)], int(a.get("window", 3)))}},
    {"name": "data_linear_regression", "description": "Fit a simple linear regression (y = mx + b) and return slope, intercept, correlation r, and r-squared.", "params": {"xs": "list", "ys": "list"}, "run": lambda a: _linear_regression([float(v) for v in a.get("xs", []) if _is_num(v)], [float(v) for v in a.get("ys", []) if _is_num(v)])},
    {"name": "data_unique", "description": "Return unique values from a list, preserving first-seen order.", "params": {"values": "list"}, "run": lambda a: {"unique": list(dict.fromkeys(a.get("values", [])))}},
    {"name": "data_xlookup", "description": "XLOOKUP-style: search a list-of-dicts for the first row where lookup_col matches lookup_value, return the value of result_col.", "params": {"rows": "list", "lookup_col": "string", "lookup_value": "any", "result_col": "string"}, "run": lambda a: {"result": next((r.get(a.get("result_col", "")) for r in a.get("rows", []) if r.get(a.get("lookup_col", "")) == a.get("lookup_value")), None)}},
    {"name": "data_csv_parse", "description": "Parse a CSV string into a list-of-dicts using the first row as headers.", "params": {"csv": "string", "delimiter": "string"}, "run": lambda a: {"rows": _csv_parse(a.get("csv", ""), a.get("delimiter", ","))}},
]
