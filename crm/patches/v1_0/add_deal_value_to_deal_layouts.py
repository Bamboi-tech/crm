import json

import frappe


def execute():
	"""
	Expose the (already existing) `deal_value` field in the CRM Deal Side Panel and Quick Entry
	layouts so users can enter a deal/order value. Dashboards already sum `deal_value`, but existing
	sites never surfaced the field in the UI. Idempotent: only inserts fields that are missing.
	"""
	_add_fields_to_layout(
		"CRM Deal-Side Panel",
		section_label="Deal",
		fields=["currency", "deal_value"],
	)
	_add_fields_to_layout(
		"CRM Deal-Quick Entry",
		section_name="deal_section",
		fields=["currency", "deal_value"],
	)


def _add_fields_to_layout(layout_name, fields, section_label=None, section_name=None):
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return

	raw = frappe.db.get_value("CRM Fields Layout", layout_name, "layout")
	if not raw:
		return

	layout = json.loads(raw)

	# Collect every field already present anywhere in the layout so we never add duplicates.
	existing = set()
	for section in layout:
		for column in section.get("columns") or []:
			existing.update(column.get("fields") or [])

	to_add = [f for f in fields if f not in existing]
	if not to_add:
		return

	target = _find_section(layout, section_label=section_label, section_name=section_name)
	if not target:
		# Fall back to appending a dedicated section if the expected one is gone.
		target = {
			"label": section_label or "Deal",
			"name": section_name or "deal_section",
			"opened": True,
			"columns": [],
		}
		layout.append(target)

	columns = target.setdefault("columns", [])
	if not columns:
		columns.append({"name": "column_deal_value", "fields": []})
	columns[0].setdefault("fields", []).extend(to_add)

	frappe.db.set_value("CRM Fields Layout", layout_name, "layout", json.dumps(layout))


def _find_section(layout, section_label=None, section_name=None):
	for section in layout:
		if section_label and section.get("label") == section_label:
			return section
		if section_name and section.get("name") == section_name:
			return section
	return None
