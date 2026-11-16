from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from .res_partner import CANALES_VENTA

MONTO_APROBACION = 50000


class SaleOrder(models.Model):
    _inherit = "sale.order"

    canal_venta = fields.Selection(
        CANALES_VENTA,
        string="Canal de venta",
        compute="_compute_canal_venta",
        store=True,
        readonly=False,
    )

    total_unidades = fields.Float(
        string="Total de unidades",
        compute="_compute_total_unidades",
        store=True,
    )

    requiere_aprobacion = fields.Boolean(
        string="Requiere aprobación",
        compute="_compute_requiere_aprobacion",
        store=True,
    )

    aprobado_por = fields.Many2one(
        "res.users",
        string="Aprobado por",
        readonly=True,
        copy=False,
    )

    pendiente_aprobacion = fields.Boolean(
        compute="_compute_pendiente_aprobacion",
    )

    @api.depends("partner_id")
    def _compute_canal_venta(self):
        for order in self:
            order.canal_venta = order.partner_id.canal_preferido

    @api.depends("order_line.product_uom_qty")
    def _compute_total_unidades(self):
        for order in self:
            order.total_unidades = sum(
                order.order_line.mapped("product_uom_qty")
            )

    @api.depends("amount_total")
    def _compute_requiere_aprobacion(self):
        for order in self:
            order.requiere_aprobacion = (
                order.amount_total > MONTO_APROBACION
            )

    @api.depends("requiere_aprobacion", "aprobado_por", "state")
    def _compute_pendiente_aprobacion(self):
        for order in self:
            order.pendiente_aprobacion = (
                order.requiere_aprobacion
                and not order.aprobado_por
                and order.state in ("draft", "sent")
            )

    def action_aprobar(self):
        if not self.env.user.has_group(
            "sales_team.group_sale_manager"
        ):
            raise AccessError(
                "Solo un administrador de ventas puede aprobar pedidos."
            )

        self.write({
            "aprobado_por": self.env.user.id,
        })

    def action_confirm(self):
        for order in self:
            if order.requiere_aprobacion and not order.aprobado_por:
                raise UserError(
                    f"El pedido {order.name} supera "
                    f"{MONTO_APROBACION:,} y debe ser aprobado "
                    "por un administrador de ventas antes de confirmarse."
                )

        return super().action_confirm()