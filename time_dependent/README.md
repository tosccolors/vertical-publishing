Time Dependent
================

This is a generic module which can be used on any Model for tracking values changes in a specific time period.

* Tracking is done for selected Model with selected Fields.
* Tracking values are based on Records with various Validity Periods.
* Validity Periods help to locate changes for specific time duration.
* And have different "Time Dependent > Configuration" with different Models (res.partner / account.account / product.template / etc).

Notes(Validation Periods in related model's record):
- Tracking can't be done for past date.
- Tracking is enabled only when configured field's value changes.
- Last tracking always consider as infinity.


Configuration
=============

* After the installation of this module, you need to add some entries in "Settings > Technical > Time Dependent > Configuration".
* Create a record in "Time Dependent > Configuration" by selecting Model (Ex: res.partner) and it's Fields (Ex: name, street, etc.). Note: Only following field types are allowed ['boolean', 'char', 'text', 'integer', 'float', 'date', 'datetime'].
* In related model's record, set Validation Period in which today's date lies.


Usage (for user)
================

* Go to related Model (Ex: res.partner) and update values of any field specified in "Time Dependent > Configuration".
* You can find the changes tracked in configured model's form view.


Usage (for module dev)
======================

* Add this time_dependent as a dependency in __manifest__.py

Below is example with Model (res.partner):

* Inherit time.dependent.thread:

.. code:: python

        class Partner(models.Model):
            _name = 'res.partner'
            _inherit = ['res.partner', 'time.dependent.thread']  //For existing Model

        #Note: For new Model
        _inherit = 'time.dependent.thread'


.. Form view::xml

         # Valid On in source model
         <field name="validity_date"/>

         # Add new tab for time faced records
         <page name="time_faced" string="Time Dependent Address Data">
            <field name="dependent_ids" readonly="1"/>
         </page>
