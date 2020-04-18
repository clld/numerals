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

    <div class="well well-small">
        Contributed by ${ctx.creator}
    </div>

    <div class="accordion" id="sidebar-accordion">
        % if getattr(request, 'map', False):
        <%util:accordion_group eid="acc-map" parent="sidebar-accordion" title="Map" open="${True}">
            ${request.map.render()}
            ${h.format_coordinates(ctx)}
        </%util:accordion_group>
        % endif
        <% v, t = u.get_variety_links(request, ctx) %>
        % if v:
          <%util:accordion_group eid="acc-var" parent="sidebar-accordion" title="${t}" open="${False}">
            ${v}
          </%util:accordion_group>
        % endif
        % if ctx.comment or ctx.url_soure_name:
        <%util:accordion_group eid="acc-com" parent="sidebar-accordion" title="Comment" open="${False}">
            % if ctx.comment:
                ${ctx.comment}
            % endif
            % if ctx.url_soure_name:
                <br />
                ${h.external_link(
                  url="https://mpi-lingweb.shh.mpg.de/numeral/{0}".format(ctx.url_soure_name),
                  label="Link to source site",
                  target="_new")}
            % endif
        </%util:accordion_group>
        % endif
    </div>
</%def>
