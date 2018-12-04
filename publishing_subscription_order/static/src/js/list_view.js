odoo.define('publishing_subscription_order.ListView', function (require) {
"use strict";

    var ListView = require('web.ListView');
    var Model = require('web.Model');

    var ListView = ListView.include({
        render_buttons: function($node) {

            // GET BUTTON REFERENCE
            this._super($node);
            if (this.$buttons) {
                var delivery_title_btn = this.$buttons.find('.generate_delivery_title');
                var delivery_list_btn = this.$buttons.find('.generate_delivery_list');
            }

            // PERFORM THE ACTION
            delivery_title_btn.on('click', this.proxy('do_delivery_title_button'));
            delivery_list_btn.on('click', this.proxy('do_delivery_list_button'));

        },
        do_delivery_title_button: function() {
            return new Model('subscription.title.delivery').call('generate_delivery_title', [[]])
                .done(function(result) {
                    location.reload(true);
                });
        },
        do_delivery_list_button: function() {
            new Model('subscription.delivery.list').call('generate_all_delivery_list', [[]])
                .done(function(result) {
                    location.reload(true);
                });
        }

    });
});