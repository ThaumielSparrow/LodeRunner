from code.render.glfunctions import *

from code.constants.common import DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT

class GeometryController:

    def __init__(self, render_offset_x, render_offset_y):

        # Calibrate the controller to render from a given base
        self.render_offset_x = render_offset_x
        self.render_offset_y = render_offset_y


    def draw_line(self, x1, y1, x2, y2, p_color, p_size = 1):

        draw_line(self.render_offset_x + x1, self.render_offset_y + y1, self.render_offset_x + x2, self.render_offset_y + y2, p_color, p_size)


    def draw_rect(self, x, y, width, height, p_color, p_current_color = (255, 255, 255), test = 0):

        draw_rect(self.render_offset_x + x, self.render_offset_y + y, width, height, p_color, p_current_color, test)


    def draw_rect_frame(self, x, y, width, height, p_color, p_frame_size, p_current_color = (255, 255, 255)):

        draw_rect_frame(self.render_offset_x + x, self.render_offset_y + y, width, height, p_color, p_frame_size, p_current_color)


    def draw_rect_with_gradient(self, x, y, width, height, color1, color2, gradient_direction):

        draw_rect_with_gradient(self.render_offset_x + x, self.render_offset_y + y, width, height, color1, color2, gradient_direction)


    def draw_rect_with_horizontal_gradient(self, x, y, width, height, color1, color2):

        draw_rect_with_horizontal_gradient(self.render_offset_x + x, self.render_offset_y + y, width, height, color1, color2)


    def draw_rect_with_vertical_gradient(self, x, y, width, height, color1, color2):

        draw_rect_with_vertical_gradient(self.render_offset_x + x, self.render_offset_y + y, width, height, color1, color2)


    def draw_circle(self, cx, cy, radius, background = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

        draw_circle(self.render_offset_x + cx, self.render_offset_y + cy, radius, background, border, accuracy, start, end, border_size)


    def draw_circle_with_gradient(self, cx, cy, radius, background1 = None, background2 = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

        draw_circle_with_gradient(self.render_offset_x + cx, self.render_offset_y + cy, radius, background1, background2, border, accuracy, start, end, border_size)


    def draw_circle_with_radial_gradient(self, cx, cy, radius, background1 = None, background2 = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

        draw_circle_with_radial_gradient(self.render_offset_x + cx, self.render_offset_y + cy, radius, background1, background2, border, accuracy, start, end, border_size)


    def draw_exclusive_circle_with_radial_gradient(self, cx, cy, radius, background1 = None, background2 = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

        draw_exclusive_circle_with_radial_gradient(self.render_offset_x + cx, self.render_offset_y + cy, radius, background1, background2, border, accuracy, start, end, border_size)


    def draw_radial_arc(self, cx, cy, start, end, radius, thickness, background, border, accuracy = 20):

        draw_radial_arc(self.render_offset_x + cx, self.render_offset_y + cy, start, end, radius, thickness, background, border, accuracy)


    def draw_radial_arc_with_gradient(self, cx, cy, start, end, radius, thickness, background1, background2, border, accuracy = 20):

        draw_radial_arc_with_gradient(self.render_offset_x + cx, self.render_offset_y + cy, start, end, radius, thickness, background1, background2, border, accuracy)


    def draw_clock_rect(self, x, y, w, h, background = None, border = None, border_size = 1, degrees = 360):

        draw_clock_rect(self.render_offset_x + x, self.render_offset_y + y, w, h, background, border, border_size, degrees)


    def draw_rounded_rect(self, x, y, w, h, background = None, border = None, border_size = 1, radius = 5, shadow = None, shadow_size = 1):

        draw_rounded_rect(self.render_offset_x + x, self.render_offset_y + y, w, h, background, border, border_size, radius, shadow, shadow_size)


    def draw_rounded_rect_with_gradient(self, x, y, w, h, background1 = None, background2 = None, border = None, border_size = 1, radius = 5, shadow = None, shadow_size = 1, gradient_direction = DIR_RIGHT):

        #draw_rounded_rect(self.render_offset_x + x, self.render_offset_y + y, w, h, background1, border, border_size, radius, shadow, shadow_size)
        draw_rounded_rect_with_gradient(self.render_offset_x + x, self.render_offset_y + y, w, h, background1, background2, border, border_size, radius, shadow, shadow_size, gradient_direction)


    def draw_rounded_rect_frame(self, x, y, w, h, color, border_size = 1, radius = 5, shadow = None, shadow_size = 1):

        draw_rounded_rect_frame(x, y, w, h, color, border_size, radius, shadow, shadow_size)


    def draw_triangle(self, x, y, w, h, background_color, border_color, orientation = DIR_UP):

        draw_triangle(self.render_offset_x + x, self.render_offset_y + y, w, h, background_color, border_color, orientation)
