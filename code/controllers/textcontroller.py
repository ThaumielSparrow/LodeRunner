class TextController:

    def __init__(self, render_offset_x, render_offset_y, text_renderer):

        # Calibrate the controller to render from a given base
        self.render_offset_x = render_offset_x
        self.render_offset_y = render_offset_y

        # Keep a reference to the associated text renderer...
        self.text_renderer = text_renderer


    def get_text_renderer(self):

        return self.text_renderer


    def get_cached_item(self, cache_key):

        return self.text_renderer.get_cache_item(cache_key)


    def render_with_wrap(self, text, x, y, color = (255, 255, 255), max_width = 1000, align = "left", letter_fade_percentages = [], render_range = None, cache_key = None, color_classes = {}, color2 = None):

        self.text_renderer.render_with_wrap(text, self.render_offset_x + x, self.render_offset_y + y, color, max_width, align, letter_fade_percentages, render_range, cache_key, color_classes, color2)


    def render(self, p_text, p_x, p_y, p_color=(255,255,255), p_max_width=-1, p_angle = None, auto_wrap = False, letter_fade_percentages = [], colors_by_offset = {}, p_color2 = None, p_align = "left", scale = 1, color_classes = {}):

        self.text_renderer.render(p_text, self.render_offset_x + p_x, self.render_offset_y + p_y, p_color, p_max_width, p_angle, auto_wrap, letter_fade_percentages, colors_by_offset, p_color2, p_align, scale, color_classes)
