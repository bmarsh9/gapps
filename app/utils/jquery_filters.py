from sqlalchemy import or_, and_
import sqlalchemy
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import load_only
from inspect import signature
import types


def create_filter(type, id, label):
    all_filters = {
        "integer": {
          "id": id,
          "label": label,
          "operators": [
              "greater",
              "less",
              "equal",
              "not_equal",
              "less_or_equal",
              "greater_or_equal",
              "between",
              "in",
              "not_in",
              "is_null",
              "is_not_null",
          ],
          "input": "number",
          "type": "integer"
        },
        "integer_select": {
          "id": id,
          "label": label,
          "input": "select",
          "type": "integer",
          "values":{},
          "operators": [
              "equal",
              "not_equal",
              "contains",
              "not_contains",
              "not_in",
              "is_null",
              "is_not_null"
          ],
        },
        "string": {
          "id": id,
          "label": label,
          "operators": [
              "equal",
              "not_equal",
              "contains",
              "not_contains",
              "ends_with",
              "not_ends_with",
              "begins_with",
              "not_begins_with",
              "in",
              "is_empty",
              "not_in",
              "is_null",
              "is_not_null"
          ],
          "input": "text",
          "type": "string"
        },
        "boolean": {
        },
        "radio": {
          "id": id,
          "label": label,
          "type": 'integer',
          "input": 'radio',
          "values": {
            1: 'Yes',
            0: 'No'
          }
        },
        "datetime": {
            "id": id,
            "label": label,
            "plugin": 'datepicker',
            "type": 'date',
            "plugin_config": {
                "format": 'yyyy/mm/dd',
                "todayBtn": 'linked',
                "todayHighlight": True,
                "autoclose": True
            }
        },
    }
    type = str(type).lower()
    if "(" in type:
        type = type.split("(")[0]
    if type == "float":
        type = "integer"
    elif type == "varchar":
        type = "string"
    return all_filters.get(type)

OPERATORS = {'equal': lambda f, a: f.__eq__(a),
             'not_equal': lambda f, a: f.__ne__(a),
             'less': lambda f, a: f.__lt__(a),
             'greater': lambda f, a: f.__gt__(a),
             'less_or_equal': lambda f, a: f.__le__(a),
             'greater_or_equal': lambda f, a: f.__ge__(a),
             'in': lambda f, a: f.in_(a),
             'not_in': lambda f, a: f.notin_(a),
             'ends_with': lambda f, a: f.like('%' + a),
             'begins_with': lambda f, a: f.like(a + '%'),
             'contains': lambda f, a: f.like('%' + a + '%'),
             'not_contains': lambda f, a: f.notlike('%' + a + '%'),
             'not_begins_with': lambda f, a: f.notlike(a + '%'),
             'not_ends_with': lambda f, a: f.notlike('%' + a),
             'is_empty': lambda f: f.__eq__(''),
             'is_not_empty': lambda f: f.__ne__(''),
             'is_null': lambda f: f.is_(None),
             'is_not_null': lambda f: f.isnot(None),
             'between': lambda f, a: f.between(a[0], a[1])
}

class Filter(object):
    def __init__(self, models, query, operators=None, tables=[]):
        model_dict = {}
        for attr in models.__dict__.values():
            if isinstance(attr, DeclarativeMeta):
                try:
                    table = sqlalchemy.inspect(attr).mapped_table
                    if table.name in tables:
                        model_dict[table.name] = attr
                except sqlalchemy.exc.NoInspectionAvailable:
                    pass
        self.models = model_dict
        self.query = query
        self.operators = operators if operators else OPERATORS

    def handle_request(self, payload, default_filter={}, default_fields={}, include_columns=True):
        data = {"data": [], "columns": []}
        if not payload:
            payload = {}

        # set filter and visible columns
        filter = payload.get("filter")
        visible = payload.get("visible")
        if not filter:
            filter = default_filter
        if not visible:
            visible = default_fields

        # execute query
        for record in self.querybuilder(filter).all():
            data["data"].append(record.as_dict())

        if include_columns:
            # get the columns of the data
            if data["data"]:
                columns = list(data["data"][0].keys())
                for index, col in enumerate(columns):
                    data["columns"].append({
                        "id": col, "data": col, "name": col,
                        "index": index, "visible": True if col in visible else False
                    })
        return data

    def querybuilder(self, rules):
        query, cond_list = self._make_query(self.query, rules)
        if rules['condition'] == 'OR':
            operator = or_
        elif rules['condition'] == 'AND':
            operator = and_
        if rules.get("fields"):
            query = query.options(load_only(*rules["fields"]))
        return query.filter(operator(*cond_list))

    """
    def add_relationships(self):
        _query = _query.querybuilder(filter)
        for name,rel in sqlalchemy.inspect(models.Agent).relationships.items():
            _query = _query.join(getattr(models.Agent,name),aliased=True)
        _query = _query.filter(models.Group.name == "Default Group")
    """

    def _make_query(self, query, rules):
        cond_list = []
        for cond in rules['rules']:
            if 'condition' not in cond:
                operator = cond['operator']
                if operator not in OPERATORS:
                    raise NotImplementedError
                try:
                    model = self.models[cond['field'].split('.')[0]]
                except KeyError:
                    raise TableNotFoundError(cond['field'].split('.')[0])
                for table in query.column_descriptions:
                   if table['entity'] == model:
                       break
                else:
                    query = query.add_entity(model)
                field = getattr(model, cond['field'].split('.')[1])
                function = OPERATORS[operator]
                arity = len(signature(function).parameters)
                if arity == 1:
                    cond_list.append(function(field))
                elif arity == 2:
                    cond_list.append(function(field, cond['value']))
            else:
                query, cond_subrule = self._make_query(query, cond)
                if cond["condition"] == "OR":
                    operator = or_
                else:
                    operator = and_
                cond_list.append(operator(*cond_subrule))
        return query, cond_list
