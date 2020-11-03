<%inherit file="app.mako"/>

<%block name="title">${_('Home')}</%block>
<%block name="brand">
    <a href="${request.resource_url(request.dataset)}" class="brand"
    style="padding-top: 7px; padding-bottom: 1px;">
    <img style="margin-top: -5px" width="32" src="${request.static_url('numerals:static/numeralbank.png')}"/>
    ${request.dataset.name}
    </a>
</%block>

${next.body()}
