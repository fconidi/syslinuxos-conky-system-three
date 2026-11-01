require('cairo')
if not conky_surface then require('cairo_xlib') end

local BLUE = {0.04, 0.75, 0.97}
local WHITE = {1, 1, 1}
local PALE = {0.78, 0.88, 0.93}
local extents = cairo_text_extents_t:create()
local logo = nil
local anchors = {196, 310, 416, 548, 672, 792}

local function color(cr, rgb, alpha)
    cairo_set_source_rgba(cr, rgb[1], rgb[2], rgb[3], alpha or 1)
end

local function value(expression)
    local text = conky_parse('${' .. expression .. '}') or ''
    text = text:gsub('^%s+', ''):gsub('%s+$', '')
    return text
end

local function number(expression)
    return tonumber(value(expression)) or 0
end

local function text(cr, x, y, content, size, rgb, align, max_width, bold)
    content = tostring(content or 'N/A')
    cairo_select_font_face(cr, 'DejaVu Sans', CAIRO_FONT_SLANT_NORMAL,
                           bold and CAIRO_FONT_WEIGHT_BOLD or CAIRO_FONT_WEIGHT_NORMAL)
    cairo_set_font_size(cr, size or 13)
    cairo_text_extents(cr, content, extents)
    if max_width and extents.x_advance > max_width then
        local characters = {}
        for char in content:gmatch('[%z\1-\127\194-\244][\128-\191]*') do
            characters[#characters + 1] = char
        end
        repeat
            characters[#characters] = nil
            content = table.concat(characters) .. '…'
            cairo_text_extents(cr, content, extents)
        until extents.x_advance <= max_width or #characters == 0
    end
    if align == 'right' then x = x - extents.x_advance end
    if align == 'center' then x = x - extents.x_advance / 2 end
    color(cr, rgb or PALE)
    cairo_move_to(cr, x, y)
    cairo_show_text(cr, content)
end

local function line(cr, x1, y1, x2, y2)
    cairo_move_to(cr, x1, y1)
    cairo_line_to(cr, x2, y2)
end

local function icon(cr, kind, x, y)
    cairo_save(cr)
    cairo_translate(cr, x, y)
    color(cr, WHITE, 0.3)
    cairo_set_line_width(cr, 1)
    cairo_new_path(cr)
    cairo_arc(cr, 0, 0, 19, 0, math.pi * 2)
    cairo_stroke(cr)
    color(cr, WHITE)
    cairo_set_line_width(cr, 1.6)
    if kind == 1 then
        cairo_rectangle(cr, -9, -7, 18, 12)
        line(cr, 0, 5, 0, 9); line(cr, -5, 9, 5, 9)
    elseif kind == 2 then
        cairo_rectangle(cr, -6, -6, 12, 12)
        for p = -4, 4, 4 do
            line(cr, p, -10, p, -6); line(cr, p, 6, p, 10)
            line(cr, -10, p, -6, p); line(cr, 6, p, 10, p)
        end
        cairo_rectangle(cr, -2, -2, 4, 4)
    elseif kind == 3 then
        cairo_rectangle(cr, -10, -6, 20, 12)
        for p = -7, 5, 6 do cairo_rectangle(cr, p, -3, 3, 5) end
        for p = -7, 7, 4 do line(cr, p, 6, p, 9) end
    elseif kind == 4 then
        cairo_move_to(cr, -11, 0); cairo_line_to(cr, -6, 0)
        cairo_line_to(cr, -3, -7); cairo_line_to(cr, 1, 8)
        cairo_line_to(cr, 5, -3); cairo_line_to(cr, 8, 0); cairo_line_to(cr, 11, 0)
    elseif kind == 5 then
        cairo_rectangle(cr, -9, -10, 18, 20)
        line(cr, -6, -4, 6, -4); line(cr, -6, 0, 6, 0)
        cairo_new_sub_path(cr); cairo_arc(cr, 4, 6, 1, 0, math.pi * 2)
    elseif kind == 6 then
        for radius = 5, 13, 4 do
            cairo_new_sub_path(cr)
            cairo_arc(cr, 0, 8, radius, math.pi * 1.22, math.pi * 1.78)
        end
        cairo_new_sub_path(cr); cairo_arc(cr, 0, 7, 1, 0, math.pi * 2)
    end
    cairo_stroke(cr)
    cairo_restore(cr)
end

local function heading(cr, index, title)
    icon(cr, index, 26, anchors[index])
    text(cr, 62, anchors[index] + 5, title, 15, WHITE, nil, 280, true)
end

local function row(cr, y, label, content)
    text(cr, 62, y, label, 12, BLUE)
    text(cr, 342, y, content, 13, PALE, 'right', 228)
end

local function bar(cr, y, percent)
    percent = math.max(0, math.min(100, percent))
    cairo_set_line_width(cr, 4)
    color(cr, BLUE, 0.22); line(cr, 64, y, 292, y); cairo_stroke(cr)
    if percent > 0 then
        color(cr, BLUE); line(cr, 64, y, 64 + 228 * percent / 100, y); cairo_stroke(cr)
    end
    text(cr, 342, y + 4, string.format('%.0f%%', percent), 12, WHITE, 'right')
end

local function data_file()
    local data = {}
    local path = os.getenv('CONKY_SYSTEM_THREE_DATA') or ''
    local handle = io.open(path, 'r')
    if handle then
        for entry in handle:lines() do
            local key, content = entry:match('^([a-z_]+)\t(.*)$')
            if key then data[key] = content end
        end
        handle:close()
    end
    return data
end

local function draw_logo(cr)
    local path = os.getenv('CONKY_SYSTEM_THREE_LOGO') or ''
    if not logo and path ~= '' then
        local image = cairo_image_surface_create_from_png(path)
        if cairo_surface_status(image) == CAIRO_STATUS_SUCCESS then logo = image
        else cairo_surface_destroy(image) end
    end
    if logo then
        local width, height = cairo_image_surface_get_width(logo), cairo_image_surface_get_height(logo)
        local factor = 64 / math.max(width, height)
        cairo_save(cr)
        cairo_translate(cr, 130 - width * factor / 2, 146)
        cairo_scale(cr, factor, factor)
        cairo_set_source_surface(cr, logo, 0, 0); cairo_paint(cr)
        cairo_restore(cr)
    else
        color(cr, BLUE); cairo_set_line_width(cr, 2)
        cairo_new_path(cr)
        cairo_arc(cr, 130, 178, 27, 0, math.pi * 2); cairo_stroke(cr)
        text(cr, 130, 186, 'L', 25, WHITE, 'center')
    end
end

local function rule(cr, y)
    color(cr, BLUE, 0.8)
    cairo_set_line_width(cr, 1)
    line(cr, 8, y, 352, y)
    cairo_stroke(cr)
end

local function ring(cr, x, y, radius, amount, width)
    amount = math.max(0, math.min(100, tonumber(amount) or 0))
    cairo_set_line_width(cr, width)
    color(cr, PALE, 0.27)
    cairo_new_path(cr)
    cairo_arc(cr, x, y, radius, math.pi * 0.7, math.pi * 2.3)
    cairo_stroke(cr)
    if amount > 0 then
        color(cr, BLUE)
        cairo_new_path(cr)
        cairo_arc(cr, x, y, radius, math.pi * 0.7, math.pi * (0.7 + 1.6 * amount / 100))
        cairo_stroke(cr)
    end
end

local function info(cr, y, label, content)
    text(cr, 10, y, label, 12, BLUE)
    text(cr, 350, y, content, 12, WHITE, 'right', 230)
end

function conky_draw()
    if not conky_window or conky_window.width <= 0 then return end
    local surface, owned
    if conky_surface then surface = conky_surface(); owned = false
    else
        surface = cairo_xlib_surface_create(conky_window.display, conky_window.drawable,
                                             conky_window.visual, conky_window.width, conky_window.height)
        owned = true
    end
    if not surface then return end
    local cr = cairo_create(surface)
    cairo_scale(cr, conky_window.width / 360, conky_window.width / 360)
    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND)
    local data = data_file()

    text(cr, 10, 32, os.date('%A'), 24, BLUE, nil, 215)
    text(cr, 10, 62, os.date('%b %Y'), 23, WHITE, nil, 210)
    text(cr, 349, 63, os.date('%d'), 56, WHITE, 'right')
    rule(cr, 75)
    ring(cr, 130, 174, 91, tonumber(os.date('%S')) * 100 / 60, 5)
    ring(cr, 130, 174, 78, tonumber(os.date('%M')) * 100 / 60, 6)
    ring(cr, 130, 174, 63, (tonumber(os.date('%H')) % 12) * 100 / 12, 5)
    draw_logo(cr)
    text(cr, 130, 292, os.date('%H:%M:%S'), 18, WHITE, 'center')
    local battery = data.battery_percent or 'N/A'
    ring(cr, 297, 153, 32, tonumber(battery) or 0, 5)
    text(cr, 297, 157, tonumber(battery) and battery .. '%' or 'N/A', 12, WHITE, 'center')
    text(cr, 297, 202, 'BATTERY', 11, BLUE, 'center')
    text(cr, 297, 240, 'UPTIME', 10, BLUE, 'center')
    text(cr, 297, 259, value('uptime_short'), 11, WHITE, 'center', 110)
    text(cr, 350, 292, data.brand or 'Linux', 12, BLUE, 'right', 112)
    rule(cr, 309)

    text(cr, 10, 332, 'PROCESSOR', 14, WHITE, nil, 340, true)
    info(cr, 353, 'Temp', data.cpu_temp or 'N/A')
    info(cr, 373, 'Load', value('loadavg'))
    info(cr, 395, 'Frequency', value('freq_g') .. ' GHz')
    info(cr, 415, 'Processes', value('processes') .. ' / ' .. value('running_processes') .. ' running')
    text(cr, 10, 453, data.cpu_model or 'Processor', 11, PALE, nil, 195)
    for i = 1, 2 do
        local x = 261 + (i - 1) * 65
        ring(cr, x, 448, 24, number('cpu cpu' .. i), 5)
        text(cr, x, 452, value('cpu cpu' .. i) .. '%', 10, WHITE, 'center')
        text(cr, x, 482, 'CPU ' .. i, 9, BLUE, 'center')
    end
    rule(cr, 500)

    text(cr, 10, 523, 'NETWORK', 14, WHITE, nil, 340, true)
    local interface = data.interface or ''
    info(cr, 545, interface ~= '' and interface or 'Interface', data.local_ip or 'N/A')
    if interface:match('^[%w_.:-]+$') and #interface <= 15 then
        info(cr, 565, 'Download', value('downspeed ' .. interface) .. '/s')
        info(cr, 585, 'Upload', value('upspeed ' .. interface) .. '/s')
        info(cr, 605, 'Transferred', '↓ ' .. value('totaldown ' .. interface) .. '  ↑ ' .. value('totalup ' .. interface))
    end
    info(cr, 628, 'External IP', data.public_ip or 'N/A')
    info(cr, 648, 'ISP', data.isp or 'N/A')
    rule(cr, 662)

    text(cr, 10, 685, 'STORAGE & MEMORY', 14, WHITE, nil, 340, true)
    local meters = {{46, 'DISK', 'fs_used_perc /'}, {161, 'RAM', 'memperc'}, {282, 'SWAP', 'swapperc'}}
    for _, m in ipairs(meters) do
        ring(cr, m[1], 729, 24, number(m[3]), 5)
        text(cr, m[1], 733, value(m[3]) .. '%', 10, WHITE, 'center')
        text(cr, m[1], 770, m[2], 10, BLUE, 'center')
    end
    info(cr, 792, 'Memory', value('mem') .. ' / ' .. value('memmax'))
    rule(cr, 806)

    text(cr, 10, 829, 'TOP PROCESSES', 14, WHITE, nil, 340, true)
    text(cr, 269, 849, 'CPU%', 10, BLUE, 'right')
    text(cr, 349, 849, 'MEM%', 10, BLUE, 'right')
    for i = 1, 3 do
        local y = 870 + (i - 1) * 19
        text(cr, 10, y, value('top name ' .. i), 11, WHITE, nil, 190)
        text(cr, 269, y, value('top cpu ' .. i), 11, PALE, 'right')
        text(cr, 349, y, value('top mem ' .. i), 11, PALE, 'right')
    end
    rule(cr, 920)
    info(cr, 939, 'System', data.os_name or 'Linux')

    cairo_destroy(cr)
    if owned then cairo_surface_destroy(surface) end
end

function conky_release()
    if logo then cairo_surface_destroy(logo); logo = nil end
    if extents then cairo_text_extents_t:destroy(extents); extents = nil end
end
