from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_, and_, asc, desc
from app.core.reports.visibility_config import VISIBILITY_REPORT_CONFIG

class ReportQueryEngine:
    def __init__(self, db: Session, config: dict = VISIBILITY_REPORT_CONFIG):
        self.db = db
        self.config = config
        self.base_model = config["base_model"]
        self.joined_models = set()

    def build_query(
        self,
        select_keys: list[str],
        filters: dict | None = None,
        sort_by: str | None = None,
        search: str | None = None,
    ):
        """
        Main entry point to build the dynamic query.
        """
        # 1. Initialize the base query
        query = self.db.query(self.base_model)

        # 2. Identify required keys for joins
        required_keys = set(select_keys)
        if filters:
            required_keys.update(filters.keys())
        if sort_by:
            sort_key = sort_by.lstrip('-')
            required_keys.add(sort_key)
        if search:
            required_keys.update(self._searchable_keys())

        # 3. Apply Joins dynamically (Handling Tuples for Aliases)
        query = self._apply_joins(query, required_keys)

        # 4. Apply Select (Projection)
        entities = []
        for key in select_keys:
            if key in self.config["fields"]:
                entities.append(self.config["fields"][key]["path"].label(key))
        
        # Always include the PK for the base model for Row Selection
        entities.append(self.base_model.id.label("base_id"))
        query = query.with_entities(*entities)

        # 5. Apply Filters
        if filters:
            query = self._apply_filters(query, filters)

        # 6. Apply Search
        if search:
            query = self._apply_search(query, search)

        # 7. Apply Sorting
        if sort_by:
            query = self._apply_sorting(query, sort_by)

        return query

    def _apply_joins(self, query, required_keys):
        """
        Enterprise Join Handler: 
        Supports both simple models and (Model, OnClause) tuples for Aliases.
        """
        for key in required_keys:
            field_def = self.config["fields"].get(key)
            if not field_def or "join_path" not in field_def:
                continue

            for step in field_def["join_path"]:
                on_clause = None
                
                # Check if the join step is a tuple (e.g., for Aliased tables)
                if isinstance(step, tuple):
                    model_to_join, on_clause = step
                else:
                    model_to_join = step

                # Only join if this specific model/alias hasn't been added to the query yet
                if model_to_join not in self.joined_models:
                    if on_clause is not None:
                        # Explicit join (used for Vendor vs Carrier distinction)
                        query = query.outerjoin(model_to_join, on_clause)
                    else:
                        # Natural join (used for standard relations)
                        query = query.outerjoin(model_to_join)
                    
                    self.joined_models.add(model_to_join)
                    
        return query

    def _apply_filters(self, query, filters):
        range_filters: dict[str, dict[str, str]] = {}
        for key, value in filters.items():
            if not value:
                continue

            if key.endswith("_start") or key.endswith("_end"):
                base_key = key.rsplit("_", 1)[0]
                range_filters.setdefault(base_key, {})[key.rsplit("_", 1)[1]] = value
                continue

            if key not in self.config["fields"]:
                continue

            field_def = self.config["fields"][key]
            column = field_def["path"]
            filter_type = field_def.get("filter_type")

            if filter_type == "search":
                query = query.filter(column.ilike(self._wildcard_like(value)))
            elif isinstance(value, list):
                query = query.filter(column.in_(value))
            else:
                query = query.filter(column == value)

        for base_key, bounds in range_filters.items():
            field_def = self.config["fields"].get(base_key)
            if not field_def:
                continue
            filter_type = field_def.get("filter_type")
            if filter_type not in ("date_range", "numeric_range"):
                continue

            column = field_def["path"]
            start_val = bounds.get("start")
            end_val = bounds.get("end")
            if start_val:
                query = query.filter(column >= start_val)
            if end_val:
                query = query.filter(column <= end_val)
        return query

    def _apply_search(self, query, search: str):
        term = (search or "").strip()
        if not term:
            return query

        clauses = []
        for key in self._searchable_keys():
            column = self.config["fields"][key]["path"]
            clauses.append(column.ilike(self._wildcard_like(term)))

        if clauses:
            query = query.filter(or_(*clauses))
        return query

    def _searchable_keys(self) -> list[str]:
        return [
            key
            for key, val in self.config["fields"].items()
            if val.get("filter_type") == "search"
        ]

    def _wildcard_like(self, value: str) -> str:
        term = (value or "").strip()
        if not term:
            return "%"
        if "*" in term or "?" in term:
            return term.replace("*", "%").replace("?", "_")
        return f"%{term}%"

    def _apply_sorting(self, query, sort_by):
        is_desc = sort_by.startswith('-')
        key = sort_by.lstrip('-')
        
        if key in self.config["fields"]:
            column = self.config["fields"][key]["path"]
            order_func = desc if is_desc else asc
            query = query.order_by(order_func(column))
        return query
