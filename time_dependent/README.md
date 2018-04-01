================
Time Dependent
================

This is a generic module which can be used on any Model for tracking values changes in a specific time period.

* Tracking is done for selected Model with selected Fields.
* Tracking values are based on Records with various Validity Periods.
* Validity Periods help to locate changes for specific time duration.
* Also reference to original record is available for all tracked records.
* And have different "Time Dependent > Model" for tracking different Models (res.partner / account.account / product.template / etc).

Notes(Validation Periods in related model's record):
- Tracking is enabled only when today's date lies in Validation Period.
- If only Validity From is set with today's date or future date, tracking is enabled from that date and Validity To is considered as infinity.
- If only Validity To is set with today's date or future date, tracking is enabled till that date and Validity From is set with today's date.
- If Validation Period is not set then tracking is disabled.
- If today's date doesn't lie in Validation Period then tracking is disabled.


Configuration
=============

* After the installation of this module, you need to add some entries in "Settings > Technical > Time Dependent > Model".
* Create a record in "Time Dependent > Model" by selecting Model (Ex: res.partner) and it's Fields (Ex: name, street, etc.). Note: Only following field types are allowed ['boolean', 'char', 'text', 'integer', 'float', 'date', 'datetime'].
* In related model's record, set Validation Period in which today's date lies.


Usage (for user)
================

* Go to related Model (Ex: res.partner) and update values of any field specified in "Time Dependent > Model".
* You can find the changes tracked in "Settings > Technical > Time Dependent > Model/Record" with original record reference.


Usage (for module dev)
======================

* Add this time_dependent as a dependency in __manifest__.py

Below is example with Model (res.partner):

* Inherit time.dependent:

.. code:: python

        class Partner(models.Model):
            _name = 'res.partner'
            _inherit = ['res.partner', 'time.dependent']  //For existing Model

        #Note: For new Model
        _inherit = 'time.dependent'

* Create fields Validity From(date_start) and Validity To(date_end):

.. code:: python

        date_start = fields.Date(string='Validity From')
        date_end = fields.Date(string='Validity To', index=True)

* Implement validation for fields Validity From and Validity To:

.. code:: python

        #Constrains for checking the validity from and validity to.
        @api.constrains('date_start', 'date_end')
        def _check_start_end_dates(self):
            for partner in self.filtered('date_end'):
                if partner.date_start and partner.date_start > partner.date_end:
                    raise ValidationError(_("Validity From can't be greater than Validity To."))