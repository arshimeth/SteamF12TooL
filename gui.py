import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk
import os
import sys
import ctypes  
from logic import (process_image, scan_for_games, find_steam_profiles, 
                   load_settings, save_settings, get_app_list_from_steam)
from languages import TRANSLATIONS


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

STEAM_BLUE = "#1F6F8B"
DONATE_RED = "#c42d33"

class CropWindow(ctk.CTkToplevel):
    def __init__(self, parent, pil_image):
        super().__init__(parent)
        self.parent = parent; self.image = pil_image; self.crop_coords = None
        self.title(parent._("crop_window_title")); self.geometry("800x600"); self.grab_set()
        self.canvas = Canvas(self, cursor="cross", highlightthickness=0); self.canvas.pack(fill="both", expand=True)
        self.button_frame = ctk.CTkFrame(self); self.button_frame.pack(fill="x", padx=10, pady=10)
        self.apply_button = ctk.CTkButton(self.button_frame, text=parent._("apply_button"), command=self.apply_crop); self.apply_button.pack(side="right", padx=5)
        self.cancel_button = ctk.CTkButton(self.button_frame, text=parent._("cancel_button"), fg_color="gray", command=self.destroy); self.cancel_button.pack(side="right", padx=5)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press); self.canvas.bind("<B1-Motion>", self.on_mouse_drag); self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.display_image()
    def display_image(self):
        self.canvas.delete("all")
        canvas_width, canvas_height = 800, 550
        img_copy = self.image.copy(); img_copy.thumbnail((canvas_width, canvas_height))
        self.photo_image = ImageTk.PhotoImage(img_copy)
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)
        self.canvas.config(width=img_copy.width, height=img_copy.height)
        self.start_x, self.start_y, self.end_x, self.end_y, self.rect = None, None, None, None, None
    def on_mouse_press(self, event):
        self.start_x, self.start_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, dash=(4, 2))
    def on_mouse_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
    def on_mouse_release(self, event):
        self.end_x, self.end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
    def apply_crop(self):
        if self.start_x is None or self.end_x is None: self.destroy(); return
        x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
        x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
        original_w, original_h = self.image.size; displayed_w, displayed_h = self.photo_image.width(), self.photo_image.height()
        ratio_w, ratio_h = original_w / displayed_w, original_h / displayed_h
        self.crop_coords = (int(x1 * ratio_w), int(y1 * ratio_h), int(x2 * ratio_w), int(y2 * ratio_h))
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        try:
            myappid = 'mycompany.steamf12tool.gui.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
        
        icon_path = resource_path('logo.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"İkon yükleme hatası: {e}")
       
        self.settings = load_settings()
        self.current_lang = self.settings.get('language', 'en')
        ctk.set_appearance_mode(self.settings.get('theme', 'Dark'))

        self.original_pil_image, self.current_pil_image, self.image_paths_list = None, None, []
        self.profiles_data, self.games_data = {}, {}
        
        self.geometry("850x650"); self.resizable(True, True)
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(1, weight=1)

        self.top_frame = ctk.CTkFrame(self, height=50); self.top_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        self.lang_options = {"Türkçe": "tr", "English": "en", "Italiano": "it", "日本語": "jp", "Français": "fr", "Русский": "ru", "中文": "zh", "العربية": "ar"}
        self.language_menu = ctk.CTkOptionMenu(self.top_frame, values=list(self.lang_options.keys()), command=self.change_language); self.language_menu.pack(side="left", padx=10, pady=10)
        self.donate_button = ctk.CTkButton(self.top_frame, text="", fg_color=DONATE_RED, command=self.open_donate_window); self.donate_button.pack(side="right", padx=10, pady=10)
        self.theme_switch = ctk.CTkSwitch(self.top_frame, text="", command=self.toggle_theme); self.theme_switch.pack(side="right", padx=10, pady=10)

        self.left_frame = ctk.CTkFrame(self); self.left_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew"); self.left_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame = ctk.CTkFrame(self.left_frame); self.preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.preview_label = ctk.CTkLabel(self.preview_frame, text=""); self.preview_label.pack(expand=True, fill="both")
        self.edit_frame = ctk.CTkFrame(self.left_frame); self.edit_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew"); self.edit_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.edit_label = ctk.CTkLabel(self.edit_frame, text="", font=ctk.CTkFont(weight="bold")); self.edit_label.grid(row=0, column=0, columnspan=4, pady=(5, 10))
        self.rotate_left_button = ctk.CTkButton(self.edit_frame, command=self.rotate_left)
        self.rotate_right_button = ctk.CTkButton(self.edit_frame, command=self.rotate_right)
        self.crop_button = ctk.CTkButton(self.edit_frame, command=self.open_crop_window)
        self.reset_button = ctk.CTkButton(self.edit_frame, fg_color="gray", command=self.reset_image)
        
        self.controls_frame = ctk.CTkFrame(self); self.controls_frame.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        self.controls_frame.grid_rowconfigure(2, weight=1)
        
        self.top_controls = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.top_controls.grid(row=0, column=0, padx=20, pady=(20,10), sticky="ew")
        self.image_button = ctk.CTkButton(self.top_controls, command=self.select_image, fg_color=STEAM_BLUE); self.image_button.pack(fill="x")
        self.image_path_var = ctk.StringVar(); self.image_label = ctk.CTkLabel(self.top_controls, textvariable=self.image_path_var, wraplength=320, font=ctk.CTkFont(size=11)); self.image_label.pack(pady=(5,0), fill="x")

        self.middle_controls = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.middle_controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.profile_label = ctk.CTkLabel(self.middle_controls, font=ctk.CTkFont(size=12, weight="bold")); self.profile_label.pack(fill="x", pady=(10,0))
        self.profile_combobox = ctk.CTkComboBox(self.middle_controls, state="disabled", command=self.on_profile_select); self.profile_combobox.pack(fill="x", pady=5)
        
        self.scan_button = ctk.CTkButton(self.middle_controls, command=self.find_and_list_games); self.scan_button.pack(fill="x", pady=10)
        
       
        self.update_list_button = ctk.CTkButton(self.middle_controls, fg_color="#555555", command=self.update_steam_app_list)
        self.update_list_button.pack(fill="x", pady=(0, 10))
        
        self.game_combobox = ctk.CTkComboBox(self.middle_controls, state="disabled", command=self.on_game_select); self.game_combobox.pack(fill="x", pady=5)
        
        self.bottom_controls = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.bottom_controls.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.manual_folder_button = ctk.CTkButton(self.bottom_controls, command=self.select_folder, fg_color="gray"); self.manual_folder_button.pack(fill="x")
        self.folder_path_var = ctk.StringVar(); self.folder_label = ctk.CTkLabel(self.bottom_controls, textvariable=self.folder_path_var, wraplength=320, font=ctk.CTkFont(size=11)); self.folder_label.pack(pady=5, fill="x")
        
        self.action_frame = ctk.CTkFrame(self.bottom_controls, fg_color="transparent"); self.action_frame.pack(fill="x", pady=10)
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.progress_frame = ctk.CTkFrame(self.action_frame, fg_color="transparent"); self.progress_frame.grid(row=0, column=0, sticky="ew")
        self.progress_label = ctk.CTkLabel(self.progress_frame, text=""); self.progress_label.pack(pady=(0,5))
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame); self.progress_bar.pack(fill="x"); self.progress_bar.set(0)
        self.process_button = ctk.CTkButton(self.action_frame, font=ctk.CTkFont(size=18, weight="bold"), height=50, command=self.run_process); self.process_button.grid(row=0, column=0, sticky="ew")
        self.process_button.tkraise()

        self.apply_initial_settings()

    def apply_initial_settings(self):
        if self.settings.get('theme', 'Dark') == 'Dark': self.theme_switch.select()
        else: self.theme_switch.deselect()
        lang_code = self.settings.get('language', 'en')
        
        try:
            lang_name = [k for k, v in self.lang_options.items() if v == lang_code][0]
            self.language_menu.set(lang_name)
        except IndexError:
            self.language_menu.set("English")
            
        self.update_ui_language(lang_code)
        self.load_profiles()

    def _(self, key, *args):
        text = TRANSLATIONS[self.current_lang].get(key, key)
        return text.format(*args) if args else text

    def update_ui_language(self, lang_code):
        self.current_lang = lang_code
        self.title(self._("window_title"))
        if not self.image_paths_list: self.preview_label.configure(text=self._("preview_placeholder"))
        self.image_button.configure(text=self._("select_image_button"))
        self.profile_label.configure(text=self._("select_profile"))
        self.scan_button.configure(text=self._("scan_games_button"))
        
 
        self.update_list_button.configure(text=self._("update_list_button"))
        
        self.manual_folder_button.configure(text=self._("manual_folder_button"))
        self.process_button.configure(text=self._("upload_button"))
        self.theme_switch.configure(text=self._("dark_mode_switch"))
        self.donate_button.configure(text=self._("donate_button"))
        if not self.image_paths_list: self.image_path_var.set(self._("no_image_selected"))
        self.folder_path_var.set(self._("no_folder_selected"))
        if not self.games_data: self.game_combobox.set(self._("game_combobox_default"))
        self.edit_label.configure(text=self._("edit_tools_label"))
        self.rotate_left_button.configure(text=self._("rotate_left_button"))
        self.rotate_right_button.configure(text=self._("rotate_right_button"))
        self.crop_button.configure(text=self._("crop_button"))
        self.reset_button.configure(text=self._("reset_button"))

    def change_language(self, choice):
        lang_code = self.lang_options[choice]
        self.settings['language'] = lang_code
        save_settings(self.settings)
        self.update_ui_language(lang_code)
        
    def toggle_theme(self):
        mode = "Dark" if self.theme_switch.get() else "Light"
        self.settings['theme'] = mode
        save_settings(self.settings)
        ctk.set_appearance_mode(mode)
    
    def open_donate_window(self):
        donate_win = ctk.CTkToplevel(self); donate_win.title(self._("donate_window_title")); donate_win.geometry("450x200"); donate_win.resizable(False, False); donate_win.grab_set()
        main_text = ctk.CTkLabel(donate_win, text=self._("donate_main_text"), font=ctk.CTkFont(size=14)); main_text.pack(pady=15, padx=20)
        iban_frame = ctk.CTkFrame(donate_win, fg_color="transparent"); iban_frame.pack(pady=10, padx=20, fill="x")
        self.iban_string = "https://steamcommunity.com/tradeoffer/new/?partner=856438463&token=BmjqXOfQ"
        iban_label = ctk.CTkLabel(iban_frame, text=self._("donate_iban_label"), font=ctk.CTkFont(size=12, weight="bold")); iban_label.pack(side="left")
        iban_entry = ctk.CTkEntry(iban_frame, width=300); iban_entry.insert(0, self.iban_string); iban_entry.configure(state="readonly"); iban_entry.pack(side="left", padx=10, fill="x")
        copy_button = ctk.CTkButton(donate_win, text=self._("donate_copy_button"), command=self.copy_iban); copy_button.pack(pady=15)

    def copy_iban(self):
        self.clipboard_clear(); self.clipboard_append(self.iban_string)
        messagebox.showinfo(self._("info"), self._("donate_copy_success"))

    def load_profiles(self):
        profiles = find_steam_profiles()
        if profiles:
            self.profiles_data = {p['persona_name']: p['user_id'] for p in profiles}
            profile_names = list(self.profiles_data.keys())
            self.profile_combobox.configure(values=profile_names, state="normal")
            last_profile = self.settings.get('last_profile')
            if last_profile and last_profile in profile_names: self.profile_combobox.set(last_profile)
            else: 
                initial_profile = profile_names[0]; self.profile_combobox.set(initial_profile); self.on_profile_select(initial_profile)
        else: self.profile_combobox.set(self._("no_profiles_found"))
        
    def on_profile_select(self, selected_profile):
        self.settings['last_profile'] = selected_profile
        save_settings(self.settings)
        self.game_combobox.set(self._("game_combobox_default")); self.game_combobox.configure(values=[self._("game_combobox_default")], state="disabled"); self.games_data = {}

    def find_and_list_games(self):
        selected_profile_name = self.profile_combobox.get()
        selected_user_id = self.profiles_data.get(selected_profile_name)
        if not selected_user_id: self.show_message({"success": False, "message_key": "no_profiles_found"}); return
        
        
        self.scan_button.configure(text=self._("scan_games_button_scanning"), state="disabled")
        self.update_idletasks()
        
        result = scan_for_games(selected_user_id)
        
        self.scan_button.configure(text=self._("scan_games_button"), state="normal")
        
        if result["success"]:
            self.games_data = {game["name"]: game["path"] for game in result["data"]}
            game_names = list(self.games_data.keys())
            self.game_combobox.configure(values=game_names, state="normal")
            self.game_combobox.set(self._("game_combobox_select"))
            messagebox.showinfo(self._("success"), self._("games_found_message", len(game_names)))
        else:
            self.show_message(result)
            self.game_combobox.set(self._("game_combobox_fail"))

    
    def update_steam_app_list(self):
        original_text = self.update_list_button.cget("text")
        self.update_list_button.configure(text=self._("update_list_loading"), state="disabled")
        self.update_idletasks()
        
        result = get_app_list_from_steam()
        
        self.update_list_button.configure(text=original_text, state="normal")
        
        if result:
            messagebox.showinfo(self._("success"), self._("update_list_success"))
       
            if self.profile_combobox.get() not in [self._("no_profiles_found"), ""]:
                self.find_and_list_games()
        else:
            messagebox.showerror(self._("error"), self._("update_list_fail"))

    def on_game_select(self, selected_game):
        path = self.games_data.get(selected_game)
        if path: self.folder_path_var.set(path)

    def select_image(self):
        paths = filedialog.askopenfilename(multiple=True, filetypes=(("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")))
        if not paths: return
        self.reset_selection()
        self.image_paths_list = list(paths)
        if len(self.image_paths_list) == 1:
            full_path = self.image_paths_list[0]
            self.image_path_var.set(os.path.basename(full_path))
            try:
                self.original_pil_image = Image.open(full_path)
                self.current_pil_image = self.original_pil_image.copy()
                self.update_preview(self.current_pil_image)
                self.show_edit_tools(True)
            except Exception as e:
                self.show_message({"success": False, "message_key": "unexpected_error", "data": str(e)})
        elif len(self.image_paths_list) > 1:
            self.preview_label.configure(image=None)  
            self.preview_label.configure(text=self._("multiple_images_selected", len(self.image_paths_list))) 
            self.image_path_var.set(self._("multiple_images_selected", len(self.image_paths_list)))
            self.show_edit_tools(False)

    def update_preview(self, pil_image):
        MAX_PREVIEW_SIZE = 400 
        try:
            img_copy = pil_image.copy()
            img_copy.thumbnail((MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE))
            ctk_img = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=img_copy.size)
            self.preview_label.configure(image=ctk_img, text="")
        except Exception as e:
            print(f"Önizleme hatası: {e}")
            self.preview_label.configure(image=None, text="Preview Error")

    def show_edit_tools(self, show=True):
        if show:
            self.rotate_left_button.grid(row=1, column=0, padx=2, pady=5, sticky="ew")
            self.rotate_right_button.grid(row=1, column=1, padx=2, pady=5, sticky="ew")
            self.crop_button.grid(row=1, column=2, padx=2, pady=5, sticky="ew")
            self.reset_button.grid(row=1, column=3, padx=2, pady=5, sticky="ew")
        else:
            self.rotate_left_button.grid_forget()
            self.rotate_right_button.grid_forget()
            self.crop_button.grid_forget()
            self.reset_button.grid_forget()
    
    def rotate_left(self):
        if self.current_pil_image:
            self.current_pil_image = self.current_pil_image.rotate(90, expand=True)
            self.update_preview(self.current_pil_image)

    def rotate_right(self):
        if self.current_pil_image:
            self.current_pil_image = self.current_pil_image.rotate(-90, expand=True)
            self.update_preview(self.current_pil_image)

    def reset_image(self):
        if self.original_pil_image:
            self.current_pil_image = self.original_pil_image.copy()
            self.update_preview(self.current_pil_image)
            
    def open_crop_window(self):
        if not self.current_pil_image: return
        crop_window = CropWindow(self, self.current_pil_image)
        self.wait_window(crop_window)
        if hasattr(crop_window, 'crop_coords') and crop_window.crop_coords:
            try:
                self.current_pil_image = self.current_pil_image.crop(crop_window.crop_coords)
                self.update_preview(self.current_pil_image)
            except Exception as e:
                self.show_message({"success": False, "message_key": "unexpected_error", "data": str(e)})

    def run_process(self):
        if not self.image_paths_list:
            self.show_message({"success": False, "message_key": "select_image_warning"}); return
        folder_path = self.folder_path_var.get()
        if self._("no_folder_selected") in folder_path or not folder_path or not os.path.exists(folder_path):
            self.show_message({"success": False, "message_key": "select_folder_warning"}); return
        
        total_count = len(self.image_paths_list)
        self.toggle_ui_elements(False)
        self.progress_frame.tkraise()

        for index, path in enumerate(self.image_paths_list):
            current_num = index + 1
            self.progress_label.configure(text=self._("upload_progress", current_num, total_count))
            self.progress_bar.set(current_num / total_count)
            self.update_idletasks()
            source_to_process = self.current_pil_image if total_count == 1 and self.current_pil_image else path
            process_image(source_to_process, folder_path)

        messagebox.showinfo(self._("success"), self._("batch_upload_complete", total_count))
        self.process_button.tkraise()
        self.toggle_ui_elements(True)
        self.reset_selection()

    def toggle_ui_elements(self, enabled=True):
        state = "normal" if enabled else "disabled"
        widgets = [self.image_button, self.profile_combobox, self.scan_button, self.update_list_button, self.game_combobox, self.manual_folder_button, self.process_button, self.language_menu, self.donate_button, self.rotate_left_button, self.rotate_right_button, self.crop_button, self.reset_button]
        for widget in widgets:
            if hasattr(self, widget.winfo_name()):
                widget.configure(state=state)

    def reset_selection(self):
        self.image_paths_list = []
        self.current_pil_image, self.original_pil_image = None, None
        self.preview_label.configure(image=None, text=self._("preview_placeholder"))
        self.image_path_var.set(self._("no_image_selected"))
        self.show_edit_tools(False)

    def show_message(self, result):
        title_key = "warning" if "warning" in result.get("message_key", "") else ("success" if result["success"] else "error")
        title = self._(title_key)
        message_key = result.get("message_key", "unexpected_error")
        message_data = result.get("data")
        message = self._(message_key, message_data) if message_data is not None else self._(message_key)
        if title_key == 'success': messagebox.showinfo(title, message)
        elif title_key == 'warning': messagebox.showwarning(title, message)
        else: messagebox.showerror(title, message)

    def select_folder(self):
        path = filedialog.askdirectory()
        if not path: return
        if os.path.basename(path).lower() == 'thumbnails':
            path = os.path.dirname(path)
            messagebox.showinfo(self._("fix"), self._("thumbnail_fix_message"))
        self.folder_path_var.set(path)

if __name__ == "__main__":
    app = App()
    app.mainloop()