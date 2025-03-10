# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from pypika.terms import Criterion
from pypika.enums import Order

import frappe
from frappe import _, _dict
from frappe.utils import cint
from frappe.utils.nestedset import get_descendants_of

from .cache import (
    get_cache,
    set_cache,
    get_cached_doc
)


# [Type Form]
@frappe.whitelist()
def type_form_setup():
    from .account import get_types_with_accounts
    
    return {
        "has_accounts": get_types_with_accounts("Expense Type")
    }


# [Type]
def get_type_lft_rgt(name: str):
    data = frappe.db.get_value("Expense Type", name, ["lft", "rgt"], as_dict=True)
    if data:
        data = _dict(data)
        data.lft = cint(data.lft)
        data.rgt = cint(data.rgt)
    
    return data


# [Type]
def type_has_descendants(lft, rgt):
    from .check import get_count
    
    return get_count(
        "Expense Type",
        {
            "lft": [">", lft],
            "rgt": ["<", rgt],
        }
    ) > 0


# [Type]
def disable_type_descendants(lft, rgt):
    doc = frappe.qb.DocType("Expense Type")
    (
        frappe.qb.update(doc)
        .set(doc.disabled, 1)
        .where(doc.disabled == 0)
        .where(doc.lft.gt(lft))
        .where(doc.rgt.lt(rgt))
    ).run()


# [Type Form]
@frappe.whitelist()
def search_types(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    from .common import parse_json
    from .search import (
        filter_search,
        prepare_data
    )
    
    dt = "Expense Type"
    doc = frappe.qb.DocType(dt)
    qry = (
        frappe.qb.from_(doc)
        .select(doc.name)
        .where(doc.disabled == 0)
    )
    
    qry = filter_search(doc, qry, dt, txt, doc.name, "name")
    
    pdoc = frappe.qb.DocType(dt).as_("parent")
    parent_qry = (
        frappe.qb.from_(pdoc)
        .select(pdoc.name)
        .where(pdoc.disabled == 0)
        .where(pdoc.is_group == 1)
        .where(pdoc.lft.lt(doc.lft))
        .where(pdoc.rgt.gt(doc.rgt))
        .orderby(doc.lft, order=Order.desc)
    )
    
    qry = qry.where(Criterion.any([
        doc.parent_type.isnull(),
        doc.parent_type == "",
        doc.parent_type.isin(parent_qry)
    ]))
    
    if "name" in filters and filters.get("name"):
        if isinstance(name, str):
            name = parse_json(name)
        
        if (
            isinstance(name, list) and len(name) == 2 and
            isinstance(name[0], str) and name[1]
        ):
            if name[0] == "=" and isinstance(name[1], str):
                qry = qry.where(doc.name == name[1])
            elif name[0] == "!=" and isinstance(name[1], str):
                qry = qry.where(doc.name != name[1])
            elif name[0] == "in" and isinstance(name[1], list):
                qry = qry.where(doc.name.isin(name[1]))
            elif name[0] == "not in" and isinstance(name[1], list):
                qry = qry.where(doc.name.notin(name[1]))
    
    if "is_group" in filters:
        is_group = 1 if cint(filters.get("is_group")) > 0 else 0
        qry = qry.where(doc.is_group == is_group)
    
    data = qry.run(as_dict=as_dict)
    
    data = prepare_data(data, dt, "name", txt, as_dict)
    
    return data


# [Type Form]
@frappe.whitelist()
def get_all_companies_accounts():
    dt = "Company"
    return frappe.get_list(
        dt,
        fields=["name", "default_expense_account"],
        filters=[
            [dt, "is_group", "=", 0]
        ]
    )


# [Type Form]
@frappe.whitelist(methods=["POST"])
def convert_group_to_item(name, parent_type=None):
    if (
        not name or not isinstance(name, str) or
        (parent_type and not isinstance(parent_type, str))
    ):
        return 0
    
    doc = get_cached_doc("Expense Type", name)
    if not doc:
        return {"error": _("The expense type does not exist.")}
    
    return doc.convert_group_to_item(parent_type);


# [Type Form]
@frappe.whitelist(methods=["POST"])
def convert_item_to_group(name):
    if not name or not isinstance(name, str):
        return 0
    
    doc = get_cached_doc("Expense Type", name)
    if not doc:
        return {"error": _("The expense type does not exist.")}
    
    return doc.convert_item_to_group();


# [Type Tree]
@frappe.whitelist()
def get_type_children(doctype, parent, is_root=False):
    return frappe.get_list(
        "Expense Type",
        fields=[
            "name as value",
            "is_group as expandable",
            "parent_type as parent"
        ],
        filters=[
            ["docstatus", "=", 0],
            [
                "ifnull(`parent_type`,\"\")",
                "=",
                "" if is_root else parent
            ]
        ]
    )


# [Type Form]
## [Item]
@frappe.whitelist(methods=["POST"])
def type_accounts(name):
    from .account import get_type_accounts
    
    if not name or not isinstance(name, str):
        return None
    
    return get_type_accounts("Expense Type", name)


## [Item]
def get_type_company_account(name: str, company: str):
    from .account import get_type_company_account_data
    
    dt = "Expense Type"
    key = f"{name}-{company}-account-data"
    cache = get_cache(dt, key)
    if cache and isinstance(cache, dict):
        return cache
    
    data = get_type_company_account_data(dt, name, company)
    if not data or not isinstance(data, dict):
        return None
    
    set_cache(dt, key, data)
    
    return data


## [Item]
def get_types_filter_query():
    doc = frappe.qb.DocType("Expense Type")
    return (
        frappe.qb.from_(doc)
        .select(doc.name)
        .where(doc.disabled == 0)
        .where(doc.is_group == 0)
    )