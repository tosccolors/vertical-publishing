FROM ghcr.io/camptocamp/odoo-project:16.0-latest
MAINTAINER tosc
COPY ./odoo/src /odoo/src
COPY ./odoo/external-src /odoo/external-src
COPY ./odoo/local-src /odoo/local-src
COPY ./requirements.txt /odoo
RUN pip install -r /odoo/requirements.txt
USER root
RUN pip install /odoo/src
# make odoo run with coverage enabled
RUN sed -ie 's/^odoo/coverage run --source=\/odoo\/local-src --omit=\/odoo\/local-src\/*\/tests\/*,*\/__manifest__.py \/usr\/local\/bin\/odoo/' /odoo/odoo-bin/runtests
USER odoo
WORKDIR /odoo
ENV DEMO=True ADDONS_PATH=/odoo/src/addons,/odoo/src/odoo/addons,/odoo/local-src,/odoo/external-src/account-analytic,/odoo/external-src/account-financial-tools,/odoo/external-src/account-invoicing,/odoo/external-src/account-payment,/odoo/external-src/bank-payment,/odoo/external-src/community-data-files,/odoo/external-src/contract,/odoo/external-src/crm,/odoo/external-src/hr,/odoo/external-src/misc,/odoo/external-src/operating-unit,/odoo/external-src/partner-contact,/odoo/external-src/queue,/odoo/external-src/reporting-engine,/odoo/external-src/server-backend,/odoo/external-src/server-ux,/odoo/external-src/timesheet,/odoo/external-src/web,/odoo/external-src/edi,/odoo/external-src/server-tools,/odoo/external-src/sale-workflow LOG_HANDLER=:INFO
