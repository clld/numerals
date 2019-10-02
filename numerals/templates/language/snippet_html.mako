<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

% if request.params.get('map_pop_up'):
  <h4>${h.link(request, ctx)}</h4>
      % if ctx.description:
          <p>${ctx.description}</p>
      % endif
  ${h.format_coordinates(ctx)}
% else:
  % if ctx.contributor:
  <b>${_('Contributor:')}</b> ${ctx.contributor}
  % endif
% endif
