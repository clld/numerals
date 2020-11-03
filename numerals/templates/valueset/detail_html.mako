<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>
<%block name="title">${ctx.language} - ${ctx.parameter}</%block>


<h2>${_('Value Set')} ${h.link(request, ctx.language)} - ${h.link(request, ctx.parameter)}</h2>

% for i, value in enumerate(ctx.values):
<div style="clear: right;">
    ${h.map_marker_img(request, value)}
    <strong>${value}</strong>
    % if value.other_form:
      - ${value.other_form}
    % endif
    % if value.comment:
      - ${value.comment}
    % endif
    % if value.is_loan:
      - ${_('is loan')}
    % endif
    % if value.org_form:
      - [<i>${_('original form')}: ${value.org_form}</i>]
    % endif
</div>
% endfor
<%def name="sidebar()">
<div class="well well-small">
<dl>
    % if ctx.parameter.concepticon_id:
        <dt>Concepticon:</dt>
        <dd>${h.external_link(url="https://concepticon.clld.org/parameters/{0}".format(ctx.parameter.concepticon_id),
            label="Concept set \"{0}\" on Concepticon".format(ctx.parameter), target="_new")}</dd>
    % endif
    <dt class="contribution">${_('Contribution')}:</dt>
    <dd class="contribution">
        ${h.link(request, ctx.contribution)}
        ${h.button('cite', onclick=h.JSModal.show(ctx.contribution.name, request.resource_url(ctx.contribution, ext='md.html')))}
    </dd>
    <dt class="language">${_('Language')}:</dt>
    <dd class="language">${h.link(request, ctx.language)}</dd>
    <dt class="parameter">${_('Parameter')}:</dt>
    <dd class="parameter">${h.link(request, ctx.parameter)}</dd>
    % if ctx.references or ctx.source:
    <dt class="source">${_('Source')}:</dt>
        % if ctx.source:
          % for s in ctx.source.split(','):
            <dd>${h.link(request, '{0}-{1}'.format(ctx.contribution.id, s), rsc='source')}</dd>
          % endfor
        % endif
        % if ctx.references:
        <dd class="source">${h.linked_references(request, ctx)|n}</dd>
        % endif
    % endif
    ${util.data(ctx, with_dl=False)}
</dl>
</div>
</%def>