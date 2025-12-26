import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk
import os
import ctypes  
from logic import (process_image, scan_for_games, find_steam_profiles, 
                   load_settings, save_settings, get_app_list_from_steam, resource_path)
from languages import TRANSLATIONS


COLOR_BG = "#1b2838"       
COLOR_PANEL = "#2a475e"    
COLOR_ACCENT = "#66c0f4"    
COLOR_ACCENT_HOVER = "#4192c2" 
COLOR_TEXT_MAIN = "#ffffff" 
COLOR_TEXT_SUB = "#c7d5e0"  
COLOR_DANGER = "#c42d33"    
COLOR_SUCCESS = "#2ea043"   

class CropWindow(ctk.CTkToplevel):
    def __init__(self, parent, pil_image):
        super().__init__(parent)
        self.parent = parent; self.image = pil_image; self.crop_coords = None
        self.title(parent._("crop_window_title"))
        self.geometry("900x700")
        self.configure(fg_color=COLOR_BG)
        self.grab_set()
        
       
        self.canvas_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.canvas_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.canvas = Canvas(self.canvas_frame, cursor="cross", highlightthickness=0, bg="#000000")
        self.canvas.pack(fill="both", expand=True)
        
      
        self.button_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, height=60, corner_radius=0)
        self.button_frame.pack(fill="x", side="bottom")
        
        self.apply_button = ctk.CTkButton(self.button_frame, text=parent._("apply_button"), 
                                          fg_color=COLOR_SUCCESS, hover_color="#8cb305", 
                                          text_color=COLOR_BG, font=("Segoe UI", 14, "bold"),
                                          command=self.apply_crop, height=40)
        self.apply_button.pack(side="right", padx=20, pady=10)
        
        self.cancel_button = ctk.CTkButton(self.button_frame, text=parent._("cancel_button"), 
                                           fg_color="transparent", border_width=1, border_color=COLOR_TEXT_SUB,
                                           command=self.destroy, height=40)
        self.cancel_button.pack(side="right", padx=10, pady=10)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.display_image()

    def display_image(self):
        self.canvas.delete("all")
       
        cw = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 860
        ch = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 550
        
        img_copy = self.image.copy()
        img_copy.thumbnail((cw, ch))
        self.photo_image = ImageTk.PhotoImage(img_copy)
       
        x_center = (cw - self.photo_image.width()) // 2
        y_center = (ch - self.photo_image.height()) // 2
        self.canvas.create_image(x_center, y_center, anchor="nw", image=self.photo_image)
       
        self.img_x, self.img_y = x_center, y_center
        self.start_x, self.start_y, self.end_x, self.end_y, self.rect = None, None, None, None, None

    def on_mouse_press(self, event):
        self.start_x, self.start_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=COLOR_ACCENT, width=2)

    def on_mouse_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_mouse_release(self, event):
        self.end_x, self.end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def apply_crop(self):
        if self.start_x is None or self.end_x is None: self.destroy(); return
      
        x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
        x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
        
      
        img_x1 = x1 - self.img_x
        img_y1 = y1 - self.img_y
        img_x2 = x2 - self.img_x
        img_y2 = y2 - self.img_y

        original_w, original_h = self.image.size
        displayed_w, displayed_h = self.photo_image.width(), self.photo_image.height()
        ratio_w = original_w / displayed_w
        ratio_h = original_h / displayed_h

        final_x1 = int(img_x1 * ratio_w)
        final_y1 = int(img_y1 * ratio_h)
        final_x2 = int(img_x2 * ratio_w)
        final_y2 = int(img_y2 * ratio_h)
        
        final_x1 = max(0, final_x1); final_y1 = max(0, final_y1)
        final_x2 = min(original_w, final_x2); final_y2 = min(original_h, final_y2)

        self.crop_coords = (final_x1, final_y1, final_x2, final_y2)
        self.destroy()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
  
        try:
            myappid = 'mycompany.steamf12tool.gui.2.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass

        icon_path = resource_path('logo.ico')
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except: pass
       
        self.settings = load_settings()
        self.current_lang = self.settings.get('language', 'en')
        ctk.set_appearance_mode("Dark") 
        
        self.title("SteamF12TooL - Ultimate Screenshot Manager")
        self.geometry("1000x700")
        self.configure(fg_color=COLOR_BG)
        
     
        self.original_pil_image, self.current_pil_image, self.image_paths_list = None, None, []
        self.profiles_data, self.games_data = {}, {}
        
        
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

       
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=0, width=280)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False) 
       
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SteamF12TooL", 
                                       font=("Segoe UI", 24, "bold"), text_color=COLOR_ACCENT)
        self.logo_label.pack(pady=(30, 10))
        self.version_label = ctk.CTkLabel(self.sidebar_frame, text="v2.0 UI Update", 
                                          font=("Segoe UI", 12), text_color=COLOR_TEXT_SUB)
        self.version_label.pack(pady=(0, 20))


        self.step1_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.step1_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_profile = ctk.CTkLabel(self.step1_frame, text="1. SELECT PROFILE", 
                                        font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_SUB, anchor="w")
        self.lbl_profile.pack(fill="x")
        
        self.profile_combobox = ctk.CTkComboBox(self.step1_frame, height=35, 
                                                fg_color=COLOR_BG, border_color=COLOR_BG,
                                                button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER,
                                                text_color=COLOR_TEXT_MAIN, state="disabled",
                                                command=self.on_profile_select)
        self.profile_combobox.pack(fill="x", pady=5)

   
        self.step2_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.step2_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_game = ctk.CTkLabel(self.step2_frame, text="2. SELECT GAME", 
                                     font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_SUB, anchor="w")
        self.lbl_game.pack(fill="x")
        
        self.scan_button = ctk.CTkButton(self.step2_frame, text="Scan Games", height=30,
                                         fg_color="transparent", border_width=1, border_color=COLOR_ACCENT,
                                         text_color=COLOR_ACCENT, hover_color=COLOR_BG,
                                         command=self.find_and_list_games)
        self.scan_button.pack(fill="x", pady=(5, 5))
        
        self.game_combobox = ctk.CTkComboBox(self.step2_frame, height=35,
                                             fg_color=COLOR_BG, border_color=COLOR_BG,
                                             button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER,
                                             state="disabled", command=self.on_game_select)
        self.game_combobox.pack(fill="x")
        
        self.update_list_button = ctk.CTkButton(self.step2_frame, text="Update Game List (DB)", height=20,
                                                fg_color="transparent", text_color=COLOR_TEXT_SUB,
                                                font=("Segoe UI", 10), hover=False,
                                                command=self.update_steam_app_list)
        self.update_list_button.pack(fill="x", pady=5)

      
        self.step3_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.step3_frame.pack(fill="x", padx=20, pady=10)
        self.lbl_folder = ctk.CTkLabel(self.step3_frame, text="MANUAL FOLDER (OPTIONAL)", 
                                       font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_SUB, anchor="w")
        self.lbl_folder.pack(fill="x")
        
        self.manual_folder_button = ctk.CTkButton(self.step3_frame, text="Browse Folder...", 
                                                  fg_color="#3d4450", hover_color="#4e5766",
                                                  command=self.select_folder)
        self.manual_folder_button.pack(fill="x", pady=5)
        self.folder_path_var = ctk.StringVar()
        self.folder_label = ctk.CTkLabel(self.step3_frame, textvariable=self.folder_path_var, 
                                         font=("Segoe UI", 9), text_color="gray", wraplength=240)
        self.folder_label.pack(fill="x")


   
        self.bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        
        self.lang_options = {"Türkçe": "tr", "English": "en", "Italiano": "it", "日本語": "jp", 
                             "Français": "fr", "Русский": "ru", "中文": "zh", "العربية": "ar"}
        self.language_menu = ctk.CTkOptionMenu(self.bottom_frame, values=list(self.lang_options.keys()), 
                                               fg_color=COLOR_BG, button_color="#3d4450",
                                               command=self.change_language)
        self.language_menu.pack(fill="x", pady=5)
        
        self.donate_button = ctk.CTkButton(self.bottom_frame, text="♥ Donate", fg_color=COLOR_DANGER, 
                                           hover_color="#a81a20", command=self.open_donate_window)
        self.donate_button.pack(fill="x", pady=5)


     
        self.main_content = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_rowconfigure(1, weight=1) 
        self.main_content.grid_columnconfigure(0, weight=1)

     
        self.header_frame = ctk.CTkFrame(self.main_content, fg_color=COLOR_PANEL, corner_radius=10)
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        self.image_button = ctk.CTkButton(self.header_frame, text="+  Select Images to Upload", 
                                          font=("Segoe UI", 16, "bold"), height=50,
                                          fg_color=COLOR_ACCENT, text_color=COLOR_BG, hover_color=COLOR_ACCENT_HOVER,
                                          command=self.select_image)
        self.image_button.pack(fill="x", padx=20, pady=20)
        self.image_path_var = ctk.StringVar()
        self.image_label = ctk.CTkLabel(self.header_frame, textvariable=self.image_path_var, 
                                        text_color=COLOR_TEXT_SUB, font=("Segoe UI", 12))
        self.image_label.pack(pady=(0, 10))

    
        self.preview_container = ctk.CTkFrame(self.main_content, fg_color="#101822", corner_radius=10, border_width=2, border_color=COLOR_PANEL)
        self.preview_container.grid(row=1, column=0, sticky="nsew")
        
        self.preview_label = ctk.CTkLabel(self.preview_container, text="No Image Selected", 
                                          font=("Segoe UI", 16), text_color=COLOR_TEXT_SUB)
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
        

        self.tools_frame = ctk.CTkFrame(self.preview_container, fg_color=COLOR_PANEL, corner_radius=20, height=50)
        
    
        btn_config = {"width": 40, "height": 40, "corner_radius": 20, "fg_color": "transparent", "hover_color": COLOR_BG, "font": ("Arial", 18)}
        self.rotate_left_button = ctk.CTkButton(self.tools_frame, text="↺", command=self.rotate_left, **btn_config)
        self.rotate_right_button = ctk.CTkButton(self.tools_frame, text="↻", command=self.rotate_right, **btn_config)
        self.crop_button = ctk.CTkButton(self.tools_frame, text="✂", command=self.open_crop_window, **btn_config)
        self.reset_button = ctk.CTkButton(self.tools_frame, text="✖", text_color=COLOR_DANGER, command=self.reset_image, **btn_config)
        
        self.rotate_left_button.pack(side="left", padx=5, pady=5)
        self.rotate_right_button.pack(side="left", padx=5, pady=5)
        self.crop_button.pack(side="left", padx=5, pady=5)
        self.reset_button.pack(side="left", padx=5, pady=5)

  
        self.action_area = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.action_area.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.action_area, height=10, progress_color=COLOR_SUCCESS)
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(self.action_area, text="", font=("Segoe UI", 10))
        self.progress_label.pack()

        self.process_button = ctk.CTkButton(self.action_area, text="UPLOAD TO STEAM FOLDER", 
                                            font=("Segoe UI", 18, "bold"), height=60,
                                            fg_color=COLOR_SUCCESS, text_color=COLOR_BG, hover_color="#8cb305",
                                            state="disabled", command=self.run_process)
        self.process_button.pack(fill="x")


        self.apply_initial_settings()
        self.show_edit_tools(False)

  
    def apply_initial_settings(self):
        lang_code = self.settings.get('language', 'en')
        try:
            lang_name = [k for k, v in self.lang_options.items() if v == lang_code][0]
            self.language_menu.set(lang_name)
        except: self.language_menu.set("English")
        self.update_ui_language(lang_code)
        self.load_profiles()

    def _(self, key, *args):
        text = TRANSLATIONS[self.current_lang].get(key, key)
        return text.format(*args) if args else text

    def update_ui_language(self, lang_code):
        self.current_lang = lang_code
 
        self.lbl_profile.configure(text=self._("select_profile").upper())
        self.scan_button.configure(text=self._("scan_games_button"))
        self.image_button.configure(text="+  " + self._("select_image_button"))
        self.process_button.configure(text=self._("upload_button").upper())
        self.manual_folder_button.configure(text=self._("manual_folder_button"))
        self.donate_button.configure(text="♥ " + self._("donate_button"))
        
        if not self.image_paths_list: self.image_path_var.set(self._("no_image_selected"))
        self.folder_path_var.set(self._("no_folder_selected"))
        if not self.games_data: self.game_combobox.set(self._("game_combobox_default"))

    def change_language(self, choice):
        lang_code = self.lang_options[choice]
        self.settings['language'] = lang_code
        save_settings(self.settings)
        self.update_ui_language(lang_code)

    def load_profiles(self):
        profiles = find_steam_profiles()
        if profiles:
            self.profiles_data = {p['persona_name']: p['user_id'] for p in profiles}
            profile_names = list(self.profiles_data.keys())
            self.profile_combobox.configure(values=profile_names, state="normal")
            last_profile = self.settings.get('last_profile')
            if last_profile and last_profile in profile_names: self.profile_combobox.set(last_profile)
            else: 
                initial = profile_names[0]; self.profile_combobox.set(initial); self.on_profile_select(initial)
        else: self.profile_combobox.set(self._("no_profiles_found"))

    def on_profile_select(self, selected_profile):
        self.settings['last_profile'] = selected_profile
        save_settings(self.settings)
        self.game_combobox.set(self._("game_combobox_default"))
        self.game_combobox.configure(state="disabled")
        self.games_data = {}
        self.scan_button.configure(state="normal")

    def find_and_list_games(self):
        selected_profile = self.profile_combobox.get()
        user_id = self.profiles_data.get(selected_profile)
        if not user_id: return
        
        self.scan_button.configure(text=self._("scan_games_button_scanning"), state="disabled")
        self.update_idletasks()
        
        result = scan_for_games(user_id)
        self.scan_button.configure(text=self._("scan_games_button"), state="normal")
        
        if result["success"]:
            self.games_data = {game["name"]: game["path"] for game in result["data"]}
            names = list(self.games_data.keys())
            self.game_combobox.configure(values=names, state="normal")
            self.game_combobox.set(self._("game_combobox_select"))
        else:
            self.show_message(result)

    def update_steam_app_list(self):
        self.update_list_button.configure(text="Downloading...", state="disabled")
        self.update_idletasks()
        result = get_app_list_from_steam()
        self.update_list_button.configure(text="Update Game List (DB)", state="normal")
        if result: 
            messagebox.showinfo("Success", self._("update_list_success"))
            if self.games_data: self.find_and_list_games() 

    def on_game_select(self, selected_game):
        path = self.games_data.get(selected_game)
        if path: 
            self.folder_path_var.set(path)
            self.check_ready_state()

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            if 'thumbnails' in path.lower(): path = os.path.dirname(path)
            self.folder_path_var.set(path)
            self.check_ready_state()

    def select_image(self):
        paths = filedialog.askopenfilename(multiple=True, filetypes=(("Images", "*.jpg *.jpeg *.png *.bmp"), ("All", "*.*")))
        if not paths: return
        
        self.image_paths_list = list(paths)
        if len(paths) == 1:
            self.image_path_var.set(os.path.basename(paths[0]))
            try:
                self.original_pil_image = Image.open(paths[0])
                self.current_pil_image = self.original_pil_image.copy()
                self.update_preview(self.current_pil_image)
                self.show_edit_tools(True)
            except Exception as e: messagebox.showerror("Error", str(e))
        else:
            self.image_path_var.set(f"{len(paths)} Files Selected")
            self.preview_label.configure(image=None, text=f"{len(paths)} Images Ready")
            self.show_edit_tools(False)
        
        self.check_ready_state()

    def update_preview(self, pil_image):
    
        w = self.preview_container.winfo_width()
        h = self.preview_container.winfo_height()
        if w < 100: w = 600 
        if h < 100: h = 400
        
        img_copy = pil_image.copy()
        img_copy.thumbnail((w-20, h-20)) 
        ctk_img = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=img_copy.size)
        self.preview_label.configure(image=ctk_img, text="")

    def show_edit_tools(self, show=True):
        if show: self.tools_frame.place(relx=0.5, rely=0.9, anchor="s")
        else: self.tools_frame.place_forget()


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
        cw = CropWindow(self, self.current_pil_image)
        self.wait_window(cw)
        if hasattr(cw, 'crop_coords') and cw.crop_coords:
            self.current_pil_image = self.current_pil_image.crop(cw.crop_coords)
            self.update_preview(self.current_pil_image)

    def check_ready_state(self):
      
        has_images = bool(self.image_paths_list)
        has_folder = self.folder_path_var.get() and self._("no_folder_selected") not in self.folder_path_var.get()
        
        if has_images and has_folder:
            self.process_button.configure(state="normal", fg_color=COLOR_SUCCESS)
        else:
            self.process_button.configure(state="disabled", fg_color=COLOR_PANEL)

    def run_process(self):
        folder = self.folder_path_var.get()
        total = len(self.image_paths_list)
        
        self.process_button.configure(state="disabled", text="PROCESSING...")
        self.progress_bar.set(0)
        
        for i, path in enumerate(self.image_paths_list):
          
            src = self.current_pil_image if total == 1 and self.current_pil_image else path
            process_image(src, folder)
            
            prog = (i+1)/total
            self.progress_bar.set(prog)
            self.progress_label.configure(text=f"Processed {i+1}/{total}")
            self.update_idletasks()
            
        messagebox.showinfo("Complete", self._("batch_upload_complete", total))
        self.process_button.configure(state="normal", text=self._("upload_button").upper())
        
       
        self.image_paths_list = []
        self.current_pil_image = None
        self.preview_label.configure(image=None, text="Upload Complete!")
        self.show_edit_tools(False)
        self.check_ready_state()

    def show_message(self, result):
        if result['success']: messagebox.showinfo("Info", self._(result['message_key']))
        else: messagebox.showerror("Error", self._(result.get('message_key', 'error')))

    def open_donate_window(self):

        dw = ctk.CTkToplevel(self); dw.title("Donate"); dw.geometry("400x200")
        ctk.CTkLabel(dw, text="Support Development <3").pack(pady=20)
        entry = ctk.CTkEntry(dw, width=300); entry.pack()
        entry.insert(0, "https://steamcommunity.com/tradeoffer/new/?partner=856438463&token=BmjqXOfQ")
        
if __name__ == "__main__":
    app = App()
    app.mainloop()