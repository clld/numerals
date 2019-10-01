<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "languages" %>
<%block name="title">${_('Language')} ${ctx.name}</%block>

<h2>${_('Language')} ${ctx.name}</h2>

${request.get_datatable('values', h.models.Value, language=ctx).render()}

<%def name="sidebar()">
    <ul class="inline codes">
        % for type_ in [h.models.IdentifierType.glottolog, h.models.IdentifierType.iso]:
            <% codes = ctx.get_identifier_objs(type_) %>
            % if len(codes):
              <li>
                  <span class="large label label-info">
                      ${type_.description}:
                      ${h.language_identifier(request, codes[0], inverted=True, style="color: white;")}
                  </span>
              </li>
            % endif
        % endfor
    </ul>

    <div style="clear: right;"> </div>

    <div class="accordion" id="sidebar-accordion">
        % if getattr(request, 'map', False):
        <%util:accordion_group eid="acc-map" parent="sidebar-accordion" title="Map" open="${True}">
            ${request.map.render()}
            ${h.format_coordinates(ctx)}
        </%util:accordion_group>
        % endif
    </div>
</%def>
