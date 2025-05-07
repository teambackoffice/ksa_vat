frappe.ui.form.on("Item", {
    custom_item_tax_template: function(frm) {
        if (frm.doc.custom_item_tax_template) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Tax Template",
                    name: frm.doc.custom_item_tax_template
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table("taxes");

                        $.each(r.message.taxes || [], function(i, tax) {
                            let row = frm.add_child("taxes");
                            row.item_tax_template = tax.item_tax_template;
                            row.tax_category = tax.tax_category;
                            row.valid_from = tax.valid_from;
                            row.minimum_net_rate = tax.minimum_net_rate;
                            row.maximum_net_rate = tax.maximum_net_rate;
                        });

                        frm.refresh_field("taxes");
                    }
                }
            });
        }
        else {
            frm.clear_table('taxes');
            frm.refresh_field('taxes');
        }
    }
    
});
