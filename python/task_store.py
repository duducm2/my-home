"""Atomic JSON persistence and validation for project tasks."""

from __future__ import annotations

import json
import os
import threading
import unicodedata
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any


STATUSES = {"pending", "in_progress", "blocked", "completed"}
ACTIVITY_TYPES = {"macro", "task"}
ICON_RULES = (
    (("porta-balcao",), "sliding-door"),
    (("vitrô", "vitro"), "bathroom-window"),
    (("janela", "janelas"), "window"),
    (("demoli", "entulho"), "demolition"),
    (("infiltra", "impermeabili"), "waterproofing-additive"),
    (("rejunte",), "grout"),
    (("telha",), "roof-tiles"),
    (("telhado",), "roofer-service"),
    (("quadro de distribuicao", "disjuntor", "dr e dps"), "breaker-panel"),
    (("conduite", "conduítes"), "conduit"),
    (("fiacao", "fiação", "circuito", "aterramento"), "electrical-wires"),
    (("tomada", "eletrica", "elétrica"), "electrician-service"),
    (("iluminacao", "iluminação"), "light-bulbs"),
    (("esgoto", "hidraul", "água", "agua"), "plumbing-pipes"),
    (("ralo", "sifonada"), "drains"),
    (("pia", "bancada", "tanque"), "sink-countertop"),
    (("vaso",), "toilet"),
    (("porcelanato", "piso", "revestimento"), "porcelain-tiles"),
    (("porta",), "interior-door"),
    (("pintura", "pintar", "acabamento"), "painter-service"),
    (("rodape", "rodapé"), "baseboards"),
    (("limpeza",), "cleaning-service"),
    (("mudanca", "mudança", "ocupante", "moveis", "móveis"), "moving-service"),
    (("cartorio", "cartório", "herdeiro", "regularizacoes do imovel"), "notary-services"),
    (("financiamento", "caixa", "avaliacao e aprovacao"), "mortgage-contract"),
    (("contrato de compra", "compra e venda"), "down-payment"),
    (("reboco", "contrapiso", "muro", "reparo", "reforma", "ampliacao", "regularizacao"), "masonry-work"),
)


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a positive integer") from exc
    if number < 1:
        raise ValueError(f"{field} must be a positive integer")
    return number


def _iso_date(value: Any, field: str) -> str:
    text = str(value or "").strip()
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc
    return text


class TaskStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "tasks.json"
        self.expenses_path = self.data_dir / "expenses.csv"
        self.icon_manifest_path = self.data_dir / "icon-manifest.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"version": 2, "tasks": [], "updated_at": now_stamp()})
        else:
            self._ensure_v2()
        self._ensure_icon_assignments()

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"tasks.json is invalid: {exc}") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
                raise ValueError("tasks.json must contain a tasks array")
            return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            payload = dict(payload)
            payload["version"] = 2
            payload["updated_at"] = now_stamp()
            temporary = self.path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            os.replace(temporary, self.path)

    def _ensure_v2(self) -> None:
        with self._lock:
            document = self._read()
            if int(document.get("version") or 1) >= 2:
                return
            tasks = [dict(item) for item in document["tasks"]]
            if not tasks:
                self._write({"version": 2, "tasks": []})
                return

            by_id = {str(item.get("id") or ""): item for item in tasks}
            summary_ids = {
                "TASK_0003": "Regularização e preparação",
                "TASK_0007": "Reforma e melhorias",
                "TASK_0009": "Pintura e acabamentos",
                "TASK_0010": "Mudança",
            }
            repository_shape = set(summary_ids).issubset(by_id)
            if repository_shape:
                for task_id, title in summary_ids.items():
                    item = by_id[task_id]
                    item["title"] = title
                    item["activity_type"] = "macro"
                    item["parent_id"] = ""
                purchase_id = self._next_id(tasks)
                purchase = {
                    "id": purchase_id,
                    "title": "Compra e financiamento",
                    "description": "Compra, regularizações documentais, Caixa e transição do imóvel.",
                    "priority": 1,
                    "sequence": 1,
                    "start_date": str(tasks[0].get("start_date") or date.today().isoformat()),
                    "end_date": str(tasks[0].get("end_date") or date.today().isoformat()),
                    "status": "pending",
                    "expense_id": "",
                    "icon_key": "home-expense",
                    "date_status": "estimated",
                    "source_refs": ["project.purchase_workflow"],
                    "activity_type": "macro",
                    "parent_id": "",
                    "created_at": now_stamp(),
                    "updated_at": now_stamp(),
                }
                tasks.append(purchase)
                macro_ids = {
                    "purchase": purchase_id,
                    "preparation": "TASK_0003",
                    "renovation": "TASK_0007",
                    "finishing": "TASK_0009",
                    "move": "TASK_0010",
                }
                for item in tasks:
                    task_id = str(item.get("id") or "")
                    if item.get("activity_type") == "macro":
                        continue
                    try:
                        number = int(task_id.removeprefix("TASK_"))
                    except ValueError:
                        number = 0
                    if 11 <= number <= 37 or 81 <= number <= 86:
                        parent_id = macro_ids["preparation"]
                    elif 38 <= number <= 67 or 87 <= number <= 96:
                        parent_id = macro_ids["renovation"]
                    elif 68 <= number <= 75:
                        parent_id = macro_ids["finishing"]
                    elif 76 <= number <= 80:
                        parent_id = macro_ids["move"]
                    else:
                        parent_id = macro_ids["purchase"]
                    item["activity_type"] = "task"
                    item["parent_id"] = parent_id
            else:
                macro_id = self._next_id(tasks)
                first = tasks[0]
                tasks.append(
                    {
                        **first,
                        "id": macro_id,
                        "title": "Projeto",
                        "description": "Macroatividade criada durante a migração.",
                        "activity_type": "macro",
                        "parent_id": "",
                    }
                )
                for item in tasks:
                    if str(item.get("id")) != macro_id:
                        item["activity_type"] = "task"
                        item["parent_id"] = macro_id

            normalized = [self._normalize(item) for item in tasks]
            normalized = self._normalize_sequences(normalized)
            self._write({"version": 2, "tasks": self._rollup(normalized)})

    def _expense_ids(self) -> set[str]:
        if not self.expenses_path.is_file():
            return set()
        with self.expenses_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return {str(row.get("id") or "") for row in csv.DictReader(handle)}

    @staticmethod
    def _search_text(*values: Any) -> str:
        text = " ".join(str(value or "") for value in values).casefold()
        return "".join(
            character
            for character in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(character)
        )

    def _expense_icons(self) -> dict[str, str]:
        if not self.expenses_path.is_file():
            return {}
        with self.expenses_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            return {
                str(row.get("id") or ""): str(row.get("icon_key") or "")
                for row in csv.DictReader(handle)
            }

    def _suggest_icon(
        self,
        task: dict[str, Any],
        tasks: list[dict[str, Any]],
        expense_icons: dict[str, str] | None = None,
    ) -> str:
        icons = self._icon_keys()
        expense_icon = (expense_icons or self._expense_icons()).get(
            str(task.get("expense_id") or "")
        )
        if expense_icon in icons:
            return expense_icon
        text = self._search_text(task.get("title"), task.get("description"))
        for terms, icon_key in ICON_RULES:
            normalized_terms = [self._search_text(term) for term in terms]
            if icon_key in icons and any(term in text for term in normalized_terms):
                return icon_key
        parent_id = str(task.get("parent_id") or "")
        parent = next(
            (item for item in tasks if str(item.get("id") or "") == parent_id),
            None,
        )
        parent_icon = str((parent or {}).get("icon_key") or "")
        if parent_icon in icons and parent_icon != "home-expense":
            return parent_icon
        return "home-expense" if "home-expense" in icons else next(iter(icons), "")

    def _ensure_icon_assignments(self) -> None:
        with self._lock:
            document = self._read()
            tasks = [dict(item) for item in document["tasks"]]
            changed = False
            expense_icons = self._expense_icons()
            for activity_type in ("macro", "task"):
                for item in tasks:
                    if str(item.get("activity_type") or "task") != activity_type:
                        continue
                    if "icon_mode" not in item:
                        item["icon_mode"] = (
                            "manual"
                            if str(item.get("icon_key") or "") not in {"", "home-expense"}
                            else "auto"
                        )
                        changed = True
                    if item["icon_mode"] == "auto":
                        suggested = self._suggest_icon(item, tasks, expense_icons)
                        if suggested and item.get("icon_key") != suggested:
                            item["icon_key"] = suggested
                            changed = True
            if changed:
                normalized = [self._normalize(item) for item in tasks]
                document["tasks"] = self._rollup(
                    self._normalize_sequences(normalized)
                )
                self._write(document)

    def _icon_keys(self) -> set[str]:
        if not self.icon_manifest_path.is_file():
            return set()
        try:
            manifest = json.loads(self.icon_manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return set()
        return set((manifest.get("icons") or {}).keys())

    def _normalize(self, task: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(task.get("id") or ""),
            "title": str(task.get("title") or ""),
            "description": str(task.get("description") or ""),
            "priority": int(task.get("priority") or 1),
            "sequence": int(task.get("sequence") or 1),
            "start_date": str(task.get("start_date") or ""),
            "end_date": str(task.get("end_date") or ""),
            "status": str(task.get("status") or "pending"),
            "expense_id": str(task.get("expense_id") or ""),
            "icon_key": str(task.get("icon_key") or "home-expense"),
            "icon_mode": str(task.get("icon_mode") or "auto"),
            "date_status": str(task.get("date_status") or "confirmed"),
            "activity_type": str(task.get("activity_type") or "task"),
            "parent_id": str(task.get("parent_id") or ""),
            "progress": int(task.get("progress") or 0),
            "source_refs": list(task.get("source_refs") or []),
            "created_at": str(task.get("created_at") or ""),
            "updated_at": str(task.get("updated_at") or ""),
        }

    @staticmethod
    def _sort_key(task: dict[str, Any]) -> tuple[Any, ...]:
        return (
            int(task.get("priority") or 1),
            int(task.get("sequence") or 1),
            str(task.get("start_date") or ""),
            str(task.get("title") or "").casefold(),
            str(task.get("id") or ""),
        )

    def _normalize_sequences(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parents = {str(item.get("parent_id") or "") for item in tasks}
        for parent_id in parents:
            siblings = sorted(
                [item for item in tasks if str(item.get("parent_id") or "") == parent_id],
                key=self._sort_key,
            )
            for sequence, task in enumerate(siblings, start=1):
                task["sequence"] = sequence
        return tasks

    def _rollup(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for macro in [item for item in tasks if item.get("activity_type") == "macro"]:
            children = [
                item for item in tasks if str(item.get("parent_id") or "") == macro["id"]
            ]
            if not children:
                macro["progress"] = 0
                continue
            macro["start_date"] = min(item["start_date"] for item in children)
            macro["end_date"] = max(item["end_date"] for item in children)
            macro["priority"] = min(int(item["priority"]) for item in children)
            macro["date_status"] = (
                "estimated"
                if any(item["date_status"] == "estimated" for item in children)
                else "confirmed"
            )
            statuses = [item["status"] for item in children]
            completed = sum(status == "completed" for status in statuses)
            macro["progress"] = round(completed * 100 / len(children))
            if "blocked" in statuses:
                macro["status"] = "blocked"
            elif completed == len(children):
                macro["status"] = "completed"
            elif any(status in {"in_progress", "completed"} for status in statuses):
                macro["status"] = "in_progress"
            else:
                macro["status"] = "pending"
        return tasks

    def _ordered(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        macros = sorted(
            [item for item in tasks if item.get("activity_type") == "macro"],
            key=self._sort_key,
        )
        ordered: list[dict[str, Any]] = []
        for macro in macros:
            ordered.append(macro)
            ordered.extend(
                sorted(
                    [item for item in tasks if item.get("parent_id") == macro["id"]],
                    key=self._sort_key,
                )
            )
        known = {item["id"] for item in ordered}
        ordered.extend(
            sorted([item for item in tasks if item["id"] not in known], key=self._sort_key)
        )
        return ordered

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks = [self._normalize(item) for item in self._read()["tasks"]]
        return self._ordered(self._rollup(tasks))

    def state(self) -> dict[str, Any]:
        tasks = self.list_tasks()
        return {
            "ok": True,
            "tasks": tasks,
            "statuses": sorted(STATUSES),
            "count": len(tasks),
            "updated_at": self._read().get("updated_at", ""),
        }

    def _validated(
        self,
        payload: dict[str, Any],
        existing: dict[str, Any] | None = None,
        all_tasks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")
        activity_type = str(payload.get("activity_type") or "task").strip()
        if activity_type not in ACTIVITY_TYPES:
            raise ValueError(f"invalid activity_type: {activity_type}")
        previous = existing or {}
        tasks = all_tasks or []
        parent_id = str(payload.get("parent_id") or "").strip()
        if previous.get("activity_type") == "macro" and activity_type == "task" and any(
            str(item.get("parent_id") or "") == str(previous.get("id") or "")
            for item in tasks
        ):
            raise ValueError("macro with child activities cannot become a task")
        if activity_type == "macro":
            parent_id = ""
        else:
            if not parent_id:
                raise ValueError("parent_id is required for task activities")
            parent = next(
                (item for item in tasks if str(item.get("id") or "") == parent_id),
                None,
            )
            if not parent or str(parent.get("activity_type") or "") != "macro":
                raise ValueError("parent_id must reference an existing macro activity")
            if parent_id == str(previous.get("id") or payload.get("id") or ""):
                raise ValueError("an activity cannot be its own parent")
        priority = _positive_int(payload.get("priority"), "priority")
        sequence = _positive_int(payload.get("sequence"), "sequence")
        start_date = _iso_date(payload.get("start_date"), "start_date")
        end_date = _iso_date(payload.get("end_date"), "end_date")
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        status = str(payload.get("status") or "pending").strip()
        if status not in STATUSES:
            raise ValueError(f"invalid status: {status}")
        date_status = str(payload.get("date_status") or "confirmed").strip()
        if date_status not in {"estimated", "confirmed"}:
            raise ValueError(f"invalid date_status: {date_status}")
        expense_id = str(payload.get("expense_id") or "").strip()
        if expense_id and expense_id not in self._expense_ids():
            raise ValueError(f"expense not found: {expense_id}")
        icon_mode = str(
            payload.get("icon_mode") or previous.get("icon_mode") or "auto"
        ).strip()
        if icon_mode not in {"auto", "manual"}:
            raise ValueError(f"invalid icon_mode: {icon_mode}")
        icon_key = str(payload.get("icon_key") or "home-expense").strip()
        icon_keys = self._icon_keys()
        if icon_mode == "manual" and icon_keys and icon_key not in icon_keys:
            raise ValueError(f"invalid icon_key: {icon_key}")
        stamp = now_stamp()
        result = {
            "id": str(previous.get("id") or payload.get("id") or ""),
            "title": title,
            "description": str(payload.get("description") or "").strip(),
            "priority": priority,
            "sequence": sequence,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "expense_id": expense_id,
            "icon_key": icon_key,
            "icon_mode": icon_mode,
            "date_status": date_status,
            "activity_type": activity_type,
            "parent_id": parent_id,
            "progress": int(previous.get("progress") or 0),
            "source_refs": list(previous.get("source_refs") or payload.get("source_refs") or []),
            "created_at": str(previous.get("created_at") or stamp),
            "updated_at": stamp,
        }
        if icon_mode == "auto":
            result["icon_key"] = self._suggest_icon(result, tasks)
        return result

    @staticmethod
    def _next_id(tasks: list[dict[str, Any]]) -> str:
        maximum = 0
        for task in tasks:
            task_id = str(task.get("id") or "")
            if task_id.startswith("TASK_"):
                try:
                    maximum = max(maximum, int(task_id[5:]))
                except ValueError:
                    pass
        return f"TASK_{maximum + 1:04d}"

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            tasks = list(document["tasks"])
            task_id = str(payload.get("id") or "").strip()
            if task_id:
                for index, current in enumerate(tasks):
                    if str(current.get("id")) == task_id:
                        tasks[index] = self._validated(payload, current, tasks)
                        break
                else:
                    raise ValueError(f"task not found: {task_id}")
            else:
                item = self._validated(payload, all_tasks=tasks)
                item["id"] = self._next_id(tasks)
                tasks.append(item)
                task_id = item["id"]
            normalized = [self._normalize(item) for item in tasks]
            document["tasks"] = self._rollup(self._normalize_sequences(normalized))
            self._write(document)
            return {"ok": True, "task_id": task_id, **self.state()}

    def delete(self, task_id: str) -> dict[str, Any]:
        task_id = str(task_id or "").strip()
        if not task_id:
            raise ValueError("task id is required")
        with self._lock:
            document = self._read()
            current = next(
                (item for item in document["tasks"] if str(item.get("id")) == task_id),
                None,
            )
            if current and str(current.get("activity_type") or "task") == "macro":
                if any(
                    str(item.get("parent_id") or "") == task_id
                    for item in document["tasks"]
                ):
                    raise ValueError(
                        "macro activity has children; reassign them before deleting it"
                    )
            tasks = [item for item in document["tasks"] if str(item.get("id")) != task_id]
            if len(tasks) == len(document["tasks"]):
                raise ValueError(f"task not found: {task_id}")
            normalized = [self._normalize(item) for item in tasks]
            document["tasks"] = self._rollup(self._normalize_sequences(normalized))
            self._write(document)
            return {"ok": True, "deleted": task_id, **self.state()}
