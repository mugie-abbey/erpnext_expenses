# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import re

from pypika.enums import Order
from pypika.terms import Criterion

import frappe
from frappe import _
from frappe.utils import cstr
from frappe.query_builder.functions import Locate


## [Internal]
__FIELD_TYPES__ = [
    "Data",
    "Text",
    "Small Text",
    "Long Text",
    "Link",
    "Select",
    "Read Only",
    "Text Editor"
]


## [Expense, Item, Type]
def filter_search(doc, qry, doctype, search, relevance, filter_column=None):
    meta = frappe.get_meta(doctype)
    if search:
        qry = qry.select(Locate(search, relevance).as_("_relevance"))
        qry = qry.orderby("_relevance", doc.modified, doc.idx, order=Order.desc)
        
        translated_search_doctypes = frappe.get_hooks("translated_search_doctypes")
        search_filters = []
        search_fields = [filter_column] if filter_column else []
        
        if meta.title_field:
            search_fields.append(meta.title_field)
        if meta.search_fields:
            search_fields.extend(meta.get_search_fields())

        for f in search_fields:
            fmeta = meta.get_field(f.strip())
            if (
                doctype not in translated_search_doctypes and
                (
                    f == "name" or
                    (fmeta and fmeta.fieldtype in __FIELD_TYPES__)
                )
            ):
                search_filters.append(doc.field(f.strip()).like("%" + search + "%"))
        
        if len(search_filters) > 1:
            qry = qry.where(Criterion.any(search_filters))
        else:
            qry = qry.where(search_filters.pop(0))
    
    if meta.get("fields", {"fieldname": "enabled", "fieldtype": "Check"}):
        qry = qry.where(doc.enabled == 1)
    if meta.get("fields", {"fieldname": "disabled", "fieldtype": "Check"}):
        qry = qry.where(doc.disabled != 1)
    
    return qry


## [Expense, Item, Type]
def prepare_data(data, dt, column, search, as_dict):
    if search and dt in frappe.get_hooks("translated_search_doctypes"):
        data = [
            v
            for v in data
            if re.search(
                re.escape(search) + ".*",
                _(v.get(column) if as_dict else v[0]),
                re.IGNORECASE
            )
        ]
    
    args = [search, as_dict]
    def relevance_sorter(key):
        value = _(key.name if args[1] else key[0])
        return (cstr(value).lower().startswith(args[0].lower()) is not True, value)
    
    data = sorted(data, key=relevance_sorter)
    
    if as_dict:
        for r in data:
            r.pop("_relevance")
    else:
        data = [r[:-1] for r in data]
    
    return data