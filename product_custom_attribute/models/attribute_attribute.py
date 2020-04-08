# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import api, models
from odoo.osv.orm import setup_modifiers


class AttributeAttribute(models.Model):
    _inherit = "attribute.attribute"

    @api.model
    def _build_attribute_field(self, vals):
        """Hide attributes fields when they are not related to
        the product's attribute_set"""

        res = super(AttributeAttribute, self)._build_attribute_field(vals)
        context = self.env.context
        if context.get('product_custom_attribute'):
            parent = res.getparent()
            if len(parent) != 0:
                parent.set("attrs",
                           "{'invisible': [('attribute_set_id', 'not in', %s)]}"
                           % self.attribute_set_ids.ids
                           )
                setup_modifiers(parent)

        return res

    @api.model
    def _build_attributes_notebook(self, vals):
        """Hide xml groups of attributes when they have no attributes fields
        related to the product's attribute_set"""

        res = super(AttributeAttribute, self)._build_attributes_notebook(vals)
        context = self.env.context
        if context.get('product_custom_attribute'):
            for group_elt in res:
                att_group = self.env['attribute.group'].search(
                    [('name', '=ilike', group_elt.get("string"))])
                att_set_ids = []
                for att in att_group.attribute_ids:
                    att_set_ids += [*att.attribute_set_ids.ids]
                domain = "[('attribute_set_id', 'not in', %s)]" % list(set(att_set_ids))
                group_elt.set('attrs', "{{'invisible' : {} }}".format(domain))
                setup_modifiers(group_elt)

        return res

    @api.multi
    def write(self, vals):
        """ When updating the domain field or deleting an attribute.option delete
        all the related attribute values in existing products that are not in the
        new domain or options"""
        res = super(AttributeAttribute, self).write(vals)
        context = self.env.context
        if context.get('product_custom_attribute'):
            if self.relation_model_id:
                try:
                    domain = ast.literal_eval(self.domain)
                except ValueError:
                    domain = []
                if domain != []:
                    domain.insert(0, '|')

                rel_model_ids = self.env[self.relation_model_id.model].search(
                    domain + [('id', 'in', [op.value_ref.id for op in self.option_ids])]
                )

                custom_field = self.name
                for product in self.env['product.template'].search([]):
                    if product.fields_get(custom_field):
                        for value in product[custom_field]:
                            if value not in rel_model_ids:
                                if self.attribute_type == 'select':
                                    product.write({custom_field: False})
                                elif self.attribute_type == 'multiselect':
                                    product.write({custom_field: [(3, value.id, 0)]})

        return res
