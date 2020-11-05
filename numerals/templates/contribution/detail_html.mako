<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>
<%block name="title">${_('Contribution')} ${ctx.id}</%block>

<h3>${_('Contribution')} ${ctx.name}</h3>

<small>Cite as</small>
<blockquote>
  ${ctx.description}
  % if ctx.doi:
    &nbsp;&nbsp;<a href="${ctx.accessURL}"><img src="https://zenodo.org/badge/DOI/${ctx.doi}.svg"/></a>
  % endif
</blockquote>
% if ctx.url:
    <p>Available online at ${h.external_link(ctx.url)}</p>
% endif
% if ctx.accessURL:
    <p>
      Data repository at ${h.external_link(ctx.accessURL)}
      % if ctx.version.find(' ') > -1:
        – <i>accessed: ${ctx.version}</i>
      % endif
    </p>
% endif

<table class="table table-nonfluid">
  <tr>
    <td>Languages</td>
    <td class="right">${ctx.language_count}</td>
  </tr>
  <tr>
    <td>Numerals</td>
    <td class="right">${ctx.parameter_count}</td>
  </tr>
  <tr>
    <td>Lexemes</td>
    <td class="right">${'{0:,}'.format(ctx.lexeme_count)}</td>
  </tr>
</table>

<% dt = request.get_datatable('values', h.models.Value, contribution=ctx) %>
% if dt:
<div>
  ${dt.render()}
</div>
% endif