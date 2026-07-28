import frappe


def execute():
	"""
	Seed the "Repeat Order" deal status (type Won) on existing sites.

	Surgical on purpose: it adds only this one status and does not call the full
	add_default_deal_statuses() seeder, so pipelines that intentionally removed default
	statuses are not resurrected. Idempotent — does nothing if the status already exists.
	"""
	if frappe.db.exists("CRM Deal Status", "Repeat Order"):
		return

	# Place it directly after "Won" when present (shifting later statuses down to make room),
	# otherwise append at the end. Avoids position collisions on customized pipelines.
	won_position = frappe.db.get_value("CRM Deal Status", "Won", "position")
	if won_position is not None:
		position = won_position + 1
		for name in frappe.get_all(
			"CRM Deal Status", filters={"position": [">=", position]}, pluck="name"
		):
			current = frappe.db.get_value("CRM Deal Status", name, "position") or 0
			frappe.db.set_value("CRM Deal Status", name, "position", current + 1)
	else:
		positions = [p for p in frappe.get_all("CRM Deal Status", pluck="position") if p is not None]
		position = (max(positions) if positions else 0) + 1

	doc = frappe.new_doc("CRM Deal Status")
	doc.deal_status = "Repeat Order"
	doc.color = "teal"
	doc.type = "Won"
	doc.probability = 100
	doc.position = position
	doc.insert(ignore_permissions=True)
