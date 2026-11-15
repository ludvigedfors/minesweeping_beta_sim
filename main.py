from turtle import color
from urllib.parse import quote

from nicegui import ui
from models import Ship, load_mines_from_json
from engine import check_for_mines, get_ship_pentagon, get_heading_line
from engine import calculate_bearing, offset_point, get_mine_x, get_mine_sensor_data
import numpy as np


# ==========================================
# 1. DATA & STATUS 
# ==========================================
mines = load_mines_from_json("minefieldbeta/mines.json")
ship = Ship(base_magnetic_signature=50.0, 
            base_acoustic_signature=50.0,
            base_pressure_signature=100.0,
            max_speed_knots=50.0,
            lat=58.8210, 
            lon=17.8857, 
            speed_knots=4.0, 
            heading_deg=0.0) 

mines_visible = True
is_running = True  # Controls whether the boat is moving or paused
mine_layers = []
triggered_mines_layer = []
ship_layer = None
ship_layer_waiting = None
heading_line_layer = None
mine_ui_elements = {}

# ==========================================
# FUNCTIONS & LOGIC
# ==========================================
def draw_mines():
    """Clears old mine layers and redraws active mines and visible mine dots."""
    global mine_layers, triggered_mines_layer

    # Remove all previously drawn mine layers from the map
    for layer in mine_layers + triggered_mines_layer:
        m.remove_layer(layer)
    mine_layers.clear()
    triggered_mines_layer.clear()

    # Activated mines always stay visible regardless of the dot toggle
    for mine in mines:
        if mine.activated:
            color = "red" if mine.severity == "high" else "orange"
            explosion_circle = m.generic_layer(
                name="circle",
                args=[[mine.lat, mine.lon], {"color": color, "radius": mine.explosion_radius, "fillOpacity": 0.3, "weight": 1}],
            )
            for segment in get_mine_x(mine.lat, mine.lon, size_m=20):
                exploded_mine = m.generic_layer(
                    name="polyline",
                    args=[segment, {"color": "black", "weight": 2}],
                )
                triggered_mines_layer.append(exploded_mine)
            triggered_mines_layer.append(explosion_circle)
        elif mines_visible:
            center_dot = m.generic_layer(
                name="circleMarker",
                args=[[mine.lat, mine.lon], {"color": "black", "fillColor": "black", "radius": 6, "fillOpacity": 1.0}],
            )

            # text that only works sometimes idk why
            label_text = f"{mine.id}: {mine.name}"
            center_dot.run_method("bindTooltip", label_text, {"permanent": True, "direction": "right", "offset": [10, 0]})

            mine_layers.append(center_dot)
            

def update_simulation():
    global ship_layer, heading_line_layer
    # Update the text
    pos_label.set_text(f"Ship position: lat {ship.lat:.4f}, lon {ship.lon:.4f} | Speed {ship.speed_knots:.2f} knots | Heading {ship.heading_deg:.1f}°")

    new_ship_layer = m.generic_layer(
        name="polygon",
        args=[
            get_ship_pentagon(ship.lat, ship.lon, ship.heading_deg),
            {"color": "black", "fillColor": "gray", "fillOpacity": 0.9, "weight": 2}
        ]
    )


    new_heading_line_layer = m.generic_layer(
        name="polyline",
        args=[
            get_heading_line(ship.lat, ship.lon, ship.heading_deg, length_m=800),
            {"color": "black", "weight": 1, "dashArray": "5, 5"}
        ]
    )

    if ship_layer is not None:
        m.remove_layer(ship_layer)
    if heading_line_layer is not None:
        m.remove_layer(heading_line_layer)

    ship_layer = new_ship_layer
    heading_line_layer = new_heading_line_layer

    if mines_visible:
        for mine in mines:
            data = get_mine_sensor_data(ship, mine)
            ui_el = mine_ui_elements[mine.id]

            ui_el["dist"].set_text(f"Avstånd till fartyg: {data['distance_m']} m")

            ui_el["mag_lbl"].set_text(f"Magnetik: {data['magnetic']} / {data['magnetic_limit']} (Gräns)")
            ui_el["mag_bar"].set_value(min(1.0, data["magnetic"] / max(1.0, data["magnetic_limit"])))

            ui_el["aco_lbl"].set_text(f"Akustik: {data['acoustic']} / {data['acoustic_limit']} (Gräns)")
            ui_el["aco_bar"].set_value(min(1.0, data["acoustic"] / max(1.0, data["acoustic_limit"])))

            ui_el["pre_lbl"].set_text(f"Tryck: {data['pressure']} / {data['pressure_limit']} (Gräns)")
            ui_el["pre_bar"].set_value(min(1.0, data["pressure"] / max(1.0, data["pressure_limit"])))

    # Check if any mines were triggered
    triggered = check_for_mines(ship, mines)
    triggered_mines_layer

    if len(triggered) == 0:
        alarm_label.set_text("No mines triggered.")
        alarm_label.classes(replace="text-green-600 font-bold")
    else:
        first_mine, distance, reason = triggered[0]
        alarm_label.set_text(f"WARNING: You have triggered the mine {first_mine.name} ({first_mine.id}) at a distance of {distance:.1f} m! Due to {reason}")
        alarm_label.classes(replace="text-red-600 font-bold")
        draw_mines()  # Redraw mines to show the triggered mine in red
        if first_mine.distance_to(ship.lat, ship.lon) <= first_mine.explosion_radius:
            toggle_running()  # Stop the boat automatically when a mine is triggered

        
            



def game_loop():
    """Runs automatically every 0.25 seconds and moves the boat forward along its course."""
    if not is_running or ship.speed_knots <= 0:
        return

    # 1 knot = 0.5144 meters per second. We multiply by 0.25 because the timer runs every 0.25 seconds.
    distance_m = ship.speed_knots * 0.5144 * 0.25

    # Calculate the boat's new position along the current course (heading_deg)
    new_lat, new_lon = offset_point(ship.lat, ship.lon, distance_m, ship.heading_deg)
    ship.lat = new_lat
    ship.lon = new_lon

    update_simulation()


# --- EVENTS (Buttons, Controls, Map Clicks) ---
def on_speed_change(event):
    ship.speed_knots = float(event.value)
    update_simulation()

def toggle_mines():
    global mines_visible
    mines_visible = not mines_visible
    datasheet_panel.set_visibility(mines_visible)
    draw_mines()



def toggle_running():
    global is_running
    is_running = not is_running
    run_button.set_text("Pause boat" if is_running else "Start boat")

def on_map_click(event):
    """Clicking the map now only changes the BOAT'S COURSE toward the point you clicked!"""
    target_lat = event.args["latlng"]["lat"]
    target_lon = event.args["latlng"]["lng"]

    ship.heading_deg = calculate_bearing(ship.lat, ship.lon, target_lat, target_lon)
    update_simulation()


# ==========================================
# BUILD THE INTERFACE (UI)
# ==========================================
    # ui.label("Information").classes("text-xl font-bold")
    # pos_label = ui.label() 
    # alarm_label = ui.label("No mines triggered.").classes("text-green-600 font-bold")

    # with ui.row().classes("w-full items-center gap-6 my-2"):
    #     ui.label("Speed (knots):").classes("font-bold")
    #     ui.slider(min=0, max=50, step=0.5, value=ship.speed_knots, on_change=on_speed_change).classes("w-64")
    #     run_button = ui.button("Pause boat", on_click=toggle_running)
    #     ui.button("Show / Hide mines", on_click=toggle_mines)

    # m = ui.leaflet(center=(ship.lat, ship.lon), zoom=14).classes("h-96 w-full")
    # m.tile_layer(url_template="https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png")
    # m.on("map-click", on_map_click)
ui.label("Information").classes("text-xl font-bold")
pos_label = ui.label()
alarm_label = ui.label("No mines triggered.").classes("text-green-600 font-bold")

with ui.row().classes("w-full items-center gap-6 my-2"):
    ui.label("Speed (knots):").classes("font-bold")
    ui.slider(min=0, max=50, step=0.5, value=ship.speed_knots, on_change=on_speed_change).classes("w-64")
    run_button = ui.button("Pause boat", on_click=toggle_running)
    ui.button("Show / Hide mines", on_click=toggle_mines)

# 3. NY LAYOUT: Karta till vänster (w-2/3) och Live-datablad till höger (w-1/3)
with ui.row().classes("w-full no-wrap gap-4"):
    
    # Vänster sida: Kartan
    m = ui.leaflet(center=(ship.lat, ship.lon), zoom=14).classes("h-[550px] w-2/3")
    m.tile_layer(url_template="https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png")
    m.on("map-click", on_map_click)

    # Höger sida: Databladspanelen
    datasheet_panel = ui.column().classes("w-1/3 gap-3")
    with datasheet_panel:
        ui.label("Live-datablad: Minor").classes("text-lg font-bold")
        
        for mine in mines:
            border_color = "border-red-500" if mine.severity == "high" else "border-orange-400"
            with ui.card().classes(f"w-full border-l-4 {border_color} p-3"):
                ui.label(f"{mine.id}: {mine.name} ({mine.severity.upper()})").classes("font-bold text-base")
                dist_lbl = ui.label("Avstånd: - m").classes("text-xs text-gray-600 mb-1")

                mag_lbl = ui.label().classes("text-xs")
                mag_bar = ui.linear_progress(value=0.0, show_value=False).classes("mb-1")

                aco_lbl = ui.label().classes("text-xs")
                aco_bar = ui.linear_progress(value=0.0, show_value=False).classes("mb-1")

                pre_lbl = ui.label().classes("text-xs")
                pre_bar = ui.linear_progress(value=0.0, show_value=False)

                mine_ui_elements[mine.id] = {
                    "dist": dist_lbl,
                    "mag_lbl": mag_lbl, "mag_bar": mag_bar,
                    "aco_lbl": aco_lbl, "aco_bar": aco_bar,
                    "pre_lbl": pre_lbl, "pre_bar": pre_bar,
                }

# Draw the initial state and start the timer
draw_mines()
update_simulation()
ui.timer(0.25, game_loop)

ui.run(title="Minefield exercise - beta", port=8080)

