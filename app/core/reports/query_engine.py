from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_, and_, asc, desc
from app.core.reports.visibility_config import VISIBILITY_REPORT_CONFIG

class ReportQueryEngine:
    def __init__(self, db: Session, config: dict = VISIBILITY_REPORT_CONFIG):
        self.db = db
        self.config = config
        self.base_model = config["base_model"]
        self.joined_models = set()

    def build_query(self, select_keys: list[str], filters: dict = None, sort_by: str = None):
        """
        Main entry point to build the dynamic query.
        """
        # 1. Initialize the base query
        # We always select the IDs for row selection logic (Enterprise requirement)
        query = self.db.query(self.base_model)

        # 2. Identify required joins based on selected columns and filters
        required_keys = set(select_keys)
        if filters:
            required_keys.update(filters.keys())
        if sort_by:
            # Handle sorting string (e.g., "-po_no" or "po_no")
            sort_key = sort_by.lstrip('-')
            required_keys.add(sort_key)

        # 3. Apply Joins dynamically
        query = self._apply_joins(query, required_keys)

        # 4. Apply Select (Projection)
        # Instead of 'select *', we only select the specific columns requested
        entities = [self.config["fields"][key]["path"].label(key) for key in select_keys]
        # Always include the PK for the base model
        entities.append(self.base_model.id.label("base_id"))
        query = query.with_entities(*entities)

        # 5. Apply Filters
        if filters:
            query = self._apply_filters(query, filters)

        # 6. Apply Sorting
        if sort_by:
            query = self._apply_sorting(query, sort_by)

        return query

    def _apply_joins(self, query, required_keys):
        """
        Crawls the join_path for each requested field and applies joins once.
        """
        for key in required_keys:
            field_def = self.config["fields"].get(key)
            if not field_def or "join_path" not in field_def:
                continue

            for model in field_def["join_path"]:
                if model not in self.joined_models:
                    # Note: In a highly advanced setup, we would handle Aliases here
                    # For now, we use simple joins based on model relationships
                    query = query.outerjoin(model)
                    self.joined_models.add(model)
        return query

    def _apply_filters(self, query, filters):
        """
        Handles exact matches and wildcards (%) automatically.
        """
        for key, value in filters.items():
            if not value or key not in self.config["fields"]:
                continue
            
            column = self.config["fields"][key]["path"]
            
            if isinstance(value, str) and ("%" in value or "_" in value):
                query = query.filter(column.ilike(value))
            elif isinstance(value, list):
                query = query.filter(column.in_(value))
            else:
                query = query.filter(column == value)
        return query

    def _apply_sorting(self, query, sort_by):
        """
        Translates '-key' to DESC and 'key' to ASC.
        """
        is_desc = sort_by.startswith('-')
        key = sort_by.lstrip('-')
        
        if key in self.config["fields"]:
            column = self.config["fields"][key]["path"]
            order_func = desc if is_desc else asc
            query = query.order_by(order_func(column))
        return query