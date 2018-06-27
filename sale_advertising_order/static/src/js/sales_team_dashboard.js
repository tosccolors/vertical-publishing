odoo.define('advertising_sales_team.dashboard', function (require) {
    "use strict";

    var sale_dashboard = require('sales_team.dashboard');

    var SalesTeamDashboardView = sale_dashboard.include({
        on_dashboard_action_clicked: function(ev){
            ev.preventDefault();
            var $action = $(ev.currentTarget);
            var action_name = $action.attr('name');
            var action_extra = $action.data('extra');
            var additional_context = {};
            // TODO: find a better way to add defaults to search view
            if (action_name === 'calendar.action_calendar_event') {
                additional_context.search_default_mymeetings = 1;
            } else if (action_name === 'crm.crm_lead_action_activities') {
                if (action_extra === 'today') {
                    additional_context.search_default_today = 1;
                } else if (action_extra === 'this_week') {
                    additional_context.search_default_this_week = 1;
                } else if (action_extra === 'overdue') {
                    additional_context.search_default_overdue = 1;
                }
            } else if (action_name === 'crm.action_your_pipeline') {
                if (action_extra === 'overdue') {
                    additional_context['search_default_overdue'] = 1;
                } else if (action_extra === 'overdue_opp') {
                    additional_context['search_default_overdue_opp'] = 1;
                }
            } else if (action_name === 'crm.crm_opportunity_report_action_graph') {
                additional_context.search_default_won = 1;
            } else if (action_name === 'sale_advertising_order.action_view_task_sale_advertising') {
                if (action_extra === 'today') {
                    additional_context.search_default_today = 1;
                } else if (action_extra === 'this_week') {
                    additional_context.search_default_this_week = 1;
                }
            } else if (action_name === 'sale.action_quotations' || action_name === 'sale_advertising_order.action_quotations_advertising' || action_name === 'publishing_subscription_order.action_quotation_subscription') {
                additional_context['search_default_my_sale_orders_filter'] = 1;
                if (action_extra === 'overdue_quotes') {
                    additional_context['search_default_overdue_quotes'] = 1;
                }
            }

            this.do_action(action_name, {additional_context: additional_context});
        },

    });

});

