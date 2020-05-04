<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

% if request.params.get('parameter'):
    <% valueset = h.get_valueset(request, ctx) %>
    <h4>${h.link(request, ctx)}</h4>
    % if valueset:
        <h5>${_('Value')}</h5>
        <ul class='unstyled'>
            % for value in valueset.values:
            <li>
                ${h.map_marker_img(request, value)}
                % if value.domainelement:
                  ${value.domainelement.name}
                % else:
                  ${h.link(request, valueset, label=str(value))}
                % endif
                ${h.format_frequency(request, value)}
            </li>
            % endfor
        </ul>
        % if valueset.references:
            <h5>${_('Source')}</h5>
            <p>${h.linked_references(request, valueset)}</p>
        % endif
    % endif
% elif request.params.get('map_pop_up'):
    <h4>${h.link(request, ctx)}</h4>
        % if ctx.description:
            <p>${ctx.description}</p>
        % endif
    ${h.format_coordinates(ctx)}
% else:
    % if ctx.creator:
      <b>${_('Contributor:')}</b> ${ctx.creator}
    % endif
% endif
