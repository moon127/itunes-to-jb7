import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from typing import Dict, Set

from .scanner import scan_directory, ScanResult
from .converter import convert_selected

CHECKED = "\u2611"
UNCHECKED = "\u2610"
PARTIAL = "\u25d0"


class JB7Converter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("iTunes to Brennan JB7 Converter")
        self.geometry("950x750")
        self.minsize(800, 600)

        self.scan_result: ScanResult = None
        self.selected_albums: Dict[str, Set[str]] = {}
        self._scanning = False
        self._converting = False

        self._setup_ui()

    def _setup_ui(self):
        dir_frame = ttk.LabelFrame(self, text="Directories", padding="5")
        dir_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Label(dir_frame, text="Source (iTunes Music):").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2
        )
        self.src_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.src_var).grid(
            row=0, column=1, sticky=tk.EW, padx=2, pady=2
        )
        ttk.Button(dir_frame, text="Browse...", command=self._browse_source).grid(
            row=0, column=2, padx=2, pady=2
        )

        ttk.Label(dir_frame, text="Destination (JB7):").grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=2
        )
        self.dest_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.dest_var).grid(
            row=1, column=1, sticky=tk.EW, padx=2, pady=2
        )
        ttk.Button(dir_frame, text="Browse...", command=self._browse_dest).grid(
            row=1, column=2, padx=2, pady=2
        )
        dir_frame.columnconfigure(1, weight=1)

        opt_frame = ttk.Frame(self, padding="5")
        opt_frame.pack(fill=tk.X, padx=5)

        ttk.Label(opt_frame, text="Min tracks for album:").pack(side=tk.LEFT)
        self.min_tracks_var = tk.IntVar(value=4)
        ttk.Spinbox(
            opt_frame, from_=1, to=99,
            textvariable=self.min_tracks_var, width=5
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            opt_frame, text="Scan Library", command=self._scan_library
        ).pack(side=tk.RIGHT, padx=5)

        self.summary_frame = ttk.LabelFrame(self, text="Library Summary", padding="5")
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)

        self.summary_text = tk.Text(
            self.summary_frame, height=6, wrap=tk.WORD, state=tk.DISABLED
        )
        self.summary_text.pack(fill=tk.X, padx=2, pady=2)

        alert_frame = ttk.Frame(self.summary_frame)
        alert_frame.pack(fill=tk.X, pady=(2, 0))

        self.btn_protected = ttk.Button(
            alert_frame, text="View Protected Albums...",
            command=self._show_protected, state=tk.DISABLED
        )
        self.btn_protected.pack(side=tk.LEFT, padx=2)

        self.btn_small = ttk.Button(
            alert_frame, text="View Small Albums...",
            command=self._show_small, state=tk.DISABLED
        )
        self.btn_small.pack(side=tk.LEFT, padx=2)

        self.btn_untracked = ttk.Button(
            alert_frame, text="View Untracked Albums...",
            command=self._show_untracked, state=tk.DISABLED
        )
        self.btn_untracked.pack(side=tk.LEFT, padx=2)

        self.btn_view_clean = ttk.Button(
            alert_frame, text="View Clean Albums...",
            command=self._show_clean, state=tk.DISABLED
        )
        self.btn_view_clean.pack(side=tk.LEFT, padx=2)

        select_frame = ttk.Frame(self.summary_frame)
        select_frame.pack(fill=tk.X, pady=(0, 2))

        self.btn_sel_clean = ttk.Button(
            select_frame, text="Select Clean",
            command=self._select_clean, state=tk.DISABLED
        )
        self.btn_sel_clean.pack(side=tk.LEFT, padx=2)

        self.btn_sel_protected = ttk.Button(
            select_frame, text="Select Protected",
            command=self._select_protected, state=tk.DISABLED
        )
        self.btn_sel_protected.pack(side=tk.LEFT, padx=2)

        self.btn_sel_small = ttk.Button(
            select_frame, text="Select Small",
            command=self._select_small, state=tk.DISABLED
        )
        self.btn_sel_small.pack(side=tk.LEFT, padx=2)

        self.btn_sel_untracked = ttk.Button(
            select_frame, text="Select Untracked",
            command=self._select_untracked, state=tk.DISABLED
        )
        self.btn_sel_untracked.pack(side=tk.LEFT, padx=2)

        content_frame = ttk.Frame(self, padding="5")
        content_frame.pack(fill=tk.BOTH, expand=True)

        tree_container = ttk.Frame(content_frame)
        tree_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            tree_container, columns=("select", "status"),
            show="tree headings", height=20
        )
        self.tree.heading("#0", text="Artist / Album")
        self.tree.heading("select", text="\u2713")
        self.tree.heading("status", text="Status")
        self.tree.column("select", width=35, anchor=tk.CENTER)
        self.tree.column("status", width=180, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(
            tree_container, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        ttk.Button(
            btn_frame, text="Select All", command=self._select_all
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            btn_frame, text="Deselect All", command=self._deselect_all
        ).pack(fill=tk.X, pady=2)
        ttk.Separator(btn_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(
            btn_frame, text="Convert Selected", command=self._convert_selected
        ).pack(fill=tk.X, pady=2)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self, variable=self.progress_var, mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(0, 2))

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _browse_source(self):
        path = filedialog.askdirectory(title="Select iTunes Music Directory")
        if path:
            self.src_var.set(path)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select JB7 Destination Directory")
        if path:
            self.dest_var.set(path)

    def _scan_library(self):
        if self._scanning or self._converting:
            return

        src = self.src_var.get().strip()
        if not src:
            messagebox.showerror("Error", "Please select a source directory")
            return
        if not Path(src).is_dir():
            messagebox.showerror("Error", f"Directory not found:\n{src}")
            return

        self._scanning = True
        self.status_var.set("Scanning library...")
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "Scanning...")
        self.summary_text.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        self.selected_albums.clear()
        self.btn_protected.config(state=tk.DISABLED)
        self.btn_small.config(state=tk.DISABLED)
        self.btn_untracked.config(state=tk.DISABLED)
        self.btn_view_clean.config(state=tk.DISABLED)
        self.btn_sel_clean.config(state=tk.DISABLED)
        self.btn_sel_protected.config(state=tk.DISABLED)
        self.btn_sel_small.config(state=tk.DISABLED)
        self.btn_sel_untracked.config(state=tk.DISABLED)

        min_tracks = self.min_tracks_var.get()

        def worker():
            try:
                result = scan_directory(src, min_tracks)
                self.after(0, self._on_scan_complete, result)
            except Exception as e:
                self.after(0, messagebox.showerror, "Scan Error", str(e))
                self.after(0, self.status_var.set, "Scan failed")
                self.after(0, self._set_scanning, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_complete(self, result: ScanResult):
        self.scan_result = result
        self._set_scanning(False)
        self._update_summary()
        self._populate_tree()
        self.status_var.set(
            f"Scan complete: {result.total_files} audio files "
            f"in {sum(len(a) for a in result.artists.values())} albums"
        )

    def _set_scanning(self, scanning: bool):
        self._scanning = scanning

    def _update_summary(self):
        if not self.scan_result:
            return

        r = self.scan_result
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)

        type_parts = []
        for ftype in sorted(r.file_types.keys()):
            free = r.drm_free.get(ftype, 0)
            prot = r.drm_protected.get(ftype, 0)
            if prot > 0:
                type_parts.append(f"{ftype}: {free} free + {prot} protected")
            else:
                type_parts.append(f"{ftype}: {free}")

        total_albums = sum(len(albums) for albums in r.artists.values())
        self.summary_text.insert(
            tk.END, f"Total audio files: {r.total_files} in {total_albums} album(s)\n"
        )
        self.summary_text.insert(tk.END, " | ".join(type_parts) + "\n")

        flagged: set = set()
        if r.protected_albums:
            total_protected = sum(
                sum(1 for t in a.tracks if t.drm_protected)
                for a in r.protected_albums
            )
            self.summary_text.insert(
                tk.END,
                f"\n\u26a0 {total_protected} DRM-protected file(s) "
                f"in {len(r.protected_albums)} album(s)",
                "warning",
            )
            self.btn_protected.config(state=tk.NORMAL)
            self.btn_sel_protected.config(state=tk.NORMAL)
            for a in r.protected_albums:
                flagged.add((a.artist, a.name))
        else:
            self.btn_protected.config(state=tk.DISABLED)
            self.btn_sel_protected.config(state=tk.DISABLED)

        if r.small_albums:
            self.summary_text.insert(
                tk.END,
                f"\n\u26a0 {len(r.small_albums)} album(s) with fewer than "
                f"{self.min_tracks_var.get()} tracks",
                "warning",
            )
            self.btn_small.config(state=tk.NORMAL)
            self.btn_sel_small.config(state=tk.NORMAL)
            for a in r.small_albums:
                flagged.add((a.artist, a.name))
        else:
            self.btn_small.config(state=tk.DISABLED)
            self.btn_sel_small.config(state=tk.DISABLED)

        if r.untracked_albums:
            self.summary_text.insert(
                tk.END,
                f"\n\u26a0 {len(r.untracked_albums)} album(s) without "
                f"track numbers",
                "warning",
            )
            self.btn_untracked.config(state=tk.NORMAL)
            self.btn_sel_untracked.config(state=tk.NORMAL)
            for a in r.untracked_albums:
                flagged.add((a.artist, a.name))
        else:
            self.btn_untracked.config(state=tk.DISABLED)
            self.btn_sel_untracked.config(state=tk.DISABLED)

        clean_count = total_albums - len(flagged)
        if clean_count > 0 and total_albums > 0:
            self.summary_text.insert(
                tk.END,
                f"\n\u2713 {clean_count} album(s) clean - ready to convert",
                "clean",
            )
            self.btn_view_clean.config(state=tk.NORMAL)
            self.btn_sel_clean.config(state=tk.NORMAL)
        else:
            self.btn_view_clean.config(state=tk.DISABLED)
            self.btn_sel_clean.config(state=tk.DISABLED)

        self.summary_text.tag_config("warning", foreground="red")
        self.summary_text.tag_config("clean", foreground="green")
        self.summary_text.config(state=tk.DISABLED)

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.tag_configure("artist", font=("", 10, "bold"))

        if not self.scan_result or not self.scan_result.artists:
            return

        for artist_name, albums in self.scan_result.artists.items():
            artist_id = self.tree.insert(
                "", "end",
                text=f"  {artist_name}",
                values=("", ""),
                tags=("artist",),
                open=False,
            )

            for album_name, album in albums.items():
                status = []
                if not album.track_count_ok:
                    status.append(f"<{self.min_tracks_var.get()}")
                if not album.has_track_numbers:
                    status.append("No#")
                if album.has_drm:
                    status.append("DRM")

                status_str = ", ".join(status) if status else "OK"
                select = UNCHECKED

                self.tree.insert(
                    artist_id, "end",
                    text=f"  {album_name} ({len(album.tracks)} trk)",
                    values=(select, status_str),
                    tags=("album", artist_name, album_name),
                )

    def _on_tree_click(self, event):
        if self._scanning or self._converting:
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        tags = self.tree.item(item_id, "tags")
        if not tags:
            return

        if tags[0] == "album":
            artist = tags[1]
            album = tags[2]
            self._toggle_album(artist, album, item_id)
        elif tags[0] == "artist":
            self._toggle_artist(item_id)

    def _toggle_album(self, artist: str, album: str, item_id: str):
        if artist not in self.selected_albums:
            self.selected_albums[artist] = set()

        if album in self.selected_albums[artist]:
            self.selected_albums[artist].discard(album)
            self.tree.set(item_id, "select", UNCHECKED)
        else:
            self.selected_albums[artist].add(album)
            self.tree.set(item_id, "select", CHECKED)

        if not self.selected_albums[artist]:
            del self.selected_albums[artist]

        parent = self.tree.parent(item_id)
        if parent:
            self._update_artist_check(parent)

    def _toggle_artist(self, artist_id: str):
        children = self.tree.get_children(artist_id)
        all_selected = all(
            self.tree.set(c, "select") == CHECKED for c in children
        )

        for child in children:
            tags = self.tree.item(child, "tags")
            if len(tags) >= 3:
                artist = tags[1]
                album = tags[2]
                if all_selected:
                    if artist in self.selected_albums:
                        self.selected_albums[artist].discard(album)
                        if not self.selected_albums[artist]:
                            del self.selected_albums[artist]
                    self.tree.set(child, "select", UNCHECKED)
                else:
                    if artist not in self.selected_albums:
                        self.selected_albums[artist] = set()
                    self.selected_albums[artist].add(album)
                    self.tree.set(child, "select", CHECKED)

        self._update_artist_check(artist_id)

    def _update_artist_check(self, artist_id: str):
        children = self.tree.get_children(artist_id)
        if not children:
            self.tree.set(artist_id, "select", "")
            return

        selected = sum(1 for c in children if self.tree.set(c, "select") == CHECKED)
        total = len(children)

        if selected == 0:
            self.tree.set(artist_id, "select", "")
        elif selected == total:
            self.tree.set(artist_id, "select", CHECKED)
        else:
            self.tree.set(artist_id, "select", PARTIAL)

    def _select_all(self):
        if not self.scan_result:
            return

        self.selected_albums.clear()
        for artist_name, albums in self.scan_result.artists.items():
            self.selected_albums[artist_name] = set(albums.keys())

        for item_id in self.tree.get_children():
            children = self.tree.get_children(item_id)
            if children:
                for child in children:
                    self.tree.set(child, "select", CHECKED)
                self.tree.set(item_id, "select", CHECKED)

    def _deselect_all(self):
        self.selected_albums.clear()
        for item_id in self.tree.get_children():
            self.tree.set(item_id, "select", "")
            for child in self.tree.get_children(item_id):
                self.tree.set(child, "select", UNCHECKED)

    def _select_matching_albums(self, predicate) -> None:
        self._deselect_all()
        if not self.scan_result:
            return
        for artist_name, albums in self.scan_result.artists.items():
            for album_name, album in albums.items():
                if predicate(album):
                    if artist_name not in self.selected_albums:
                        self.selected_albums[artist_name] = set()
                    self.selected_albums[artist_name].add(album_name)
        self._sync_tree_selection()

    def _sync_tree_selection(self) -> None:
        for item_id in self.tree.get_children():
            children = self.tree.get_children(item_id)
            for child in children:
                tags = self.tree.item(child, "tags")
                if len(tags) >= 3:
                    artist = tags[1]
                    album = tags[2]
                    if artist in self.selected_albums and album in self.selected_albums[artist]:
                        self.tree.set(child, "select", CHECKED)
                    else:
                        self.tree.set(child, "select", UNCHECKED)
            if children:
                self._update_artist_check(item_id)

    def _select_clean(self):
        r = self.scan_result
        if not r:
            return
        flagged: set = set()
        for a in r.protected_albums:
            flagged.add((a.artist, a.name))
        for a in r.small_albums:
            flagged.add((a.artist, a.name))
        for a in r.untracked_albums:
            flagged.add((a.artist, a.name))

        def is_clean(album):
            return (album.artist, album.name) not in flagged

        self._select_matching_albums(is_clean)

    def _select_protected(self):
        if not self.scan_result:
            return
        flagged = {(a.artist, a.name) for a in self.scan_result.protected_albums}

        def is_in(album):
            return (album.artist, album.name) in flagged

        self._select_matching_albums(is_in)

    def _select_small(self):
        if not self.scan_result:
            return
        flagged = {(a.artist, a.name) for a in self.scan_result.small_albums}

        def is_in(album):
            return (album.artist, album.name) in flagged

        self._select_matching_albums(is_in)

    def _select_untracked(self):
        if not self.scan_result:
            return
        flagged = {(a.artist, a.name) for a in self.scan_result.untracked_albums}

        def is_in(album):
            return (album.artist, album.name) in flagged

        self._select_matching_albums(is_in)

    def _collect_selected_albums(self):
        selected = {}
        if not self.scan_result:
            return selected

        for artist, album_names in self.selected_albums.items():
            if artist in self.scan_result.artists:
                for album_name in album_names:
                    if album_name in self.scan_result.artists[artist]:
                        if artist not in selected:
                            selected[artist] = {}
                        selected[artist][album_name] = (
                            self.scan_result.artists[artist][album_name]
                        )
        return selected

    def _convert_selected(self):
        if self._scanning or self._converting:
            return

        if not self.scan_result:
            messagebox.showinfo("No Data", "Please scan a library first")
            return

        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showerror("Error", "Please select a destination directory")
            return

        selected = self._collect_selected_albums()
        if not selected:
            messagebox.showinfo("No Selection", "Please select albums to convert")
            return

        warnings = []
        for artist, albums in selected.items():
            for album_name, album in albums.items():
                issues = []
                if not album.track_count_ok:
                    issues.append(
                        f"only {len(album.tracks)} tracks "
                        f"(< {self.min_tracks_var.get()})"
                    )
                if not album.has_track_numbers:
                    issues.append("no track numbers")
                if album.has_drm:
                    issues.append("DRM protected")
                if issues:
                    warnings.append(
                        f"{artist} / {album_name}: {', '.join(issues)}"
                    )

        album_count = sum(len(a) for a in selected.values())
        msg = f"Convert {album_count} album(s) to JB7 format?"
        if warnings:
            msg += (
                "\n\nNote the following items:\n"
                + "\n".join(f"\u2022 {w}" for w in warnings)
            )

        if not messagebox.askyesno("Confirm Conversion", msg):
            return

        self._converting = True
        self.status_var.set("Converting...")
        self.progress_var.set(0)

        total_files = sum(
            len(a.tracks) for albums in selected.values() for a in albums.values()
        )
        self.progress_bar["maximum"] = total_files

        copied = [0]

        def progress_callback(msg: str):
            copied[0] += 1
            self.after(0, self.progress_var.set, copied[0])
            self.after(0, self.status_var.set, msg)

        def worker():
            try:
                total = convert_selected(selected, dest, progress_callback)
                self.after(0, self._on_convert_complete, total)
            except Exception as e:
                self.after(0, messagebox.showerror, "Conversion Error", str(e))
                self.after(0, self.status_var.set, "Conversion failed")
                self.after(0, self._set_converting, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_convert_complete(self, total: int):
        self._converting = False
        self._deselect_all()
        self.progress_var.set(0)
        self.status_var.set(f"Conversion complete: {total} files copied")
        messagebox.showinfo(
            "Complete", f"Successfully converted {total} file(s) to JB7 format."
        )

    def _set_converting(self, val: bool):
        self._converting = val

    def _show_clean(self):
        if not self.scan_result:
            return
        flagged: set = set()
        for a in self.scan_result.protected_albums:
            flagged.add((a.artist, a.name))
        for a in self.scan_result.small_albums:
            flagged.add((a.artist, a.name))
        for a in self.scan_result.untracked_albums:
            flagged.add((a.artist, a.name))
        clean = [
            a for artist_albums in self.scan_result.artists.values()
            for a in artist_albums.values()
            if (a.artist, a.name) not in flagged
        ]
        self._show_album_dialog("Clean Albums", clean, None)

    def _show_protected(self):
        if self.scan_result:
            self._show_album_dialog(
                "DRM-Protected Albums",
                self.scan_result.protected_albums,
                lambda t: t.drm_protected,
            )

    def _show_small(self):
        if self.scan_result:
            self._show_album_dialog(
                f"Albums With <{self.min_tracks_var.get()} Tracks",
                self.scan_result.small_albums,
                None,
            )

    def _show_untracked(self):
        if self.scan_result:
            self._show_album_dialog(
                "Albums Without Track Numbers",
                self.scan_result.untracked_albums,
                lambda t: not t.has_track_number,
            )

    def _show_album_dialog(self, title: str, albums, highlight_filter=None):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("650x450")
        dialog.transient(self)
        dialog.grab_set()

        text = tk.Text(dialog, wrap=tk.WORD, font=("", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(text, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for album in albums:
            text.insert(tk.END, f"{album.artist} / {album.name}\n", "header")
            for track in album.tracks:
                if highlight_filter and highlight_filter(track):
                    text.insert(tk.END, f"  {track.filename}\n", "highlight")
                else:
                    text.insert(tk.END, f"  {track.filename}\n")
            text.insert(tk.END, "\n")

        text.tag_config("header", font=("", 10, "bold"))
        text.tag_config("highlight", foreground="red", font=("", 10, "bold"))
        text.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5)
        ttk.Button(
            btn_frame, text="Save as text file...",
            command=lambda: self._save_dialog_text(title, albums, highlight_filter),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _save_dialog_text(self, title: str, albums, highlight_filter=None) -> None:
        lines = [f"{title}\n", f"{'=' * len(title)}\n\n"]
        for album in albums:
            lines.append(f"{album.artist} / {album.name}\n")
            for track in album.tracks:
                flag = ""
                if highlight_filter and highlight_filter(track):
                    flag = "  [FLAGGED]"
                lines.append(f"  {track.filename}{flag}\n")
            lines.append("\n")

        path = filedialog.asksaveasfilename(
            title="Save report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"{title.lower().replace(' ', '_')}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w") as f:
                f.writelines(lines)
        except (IOError, OSError) as e:
            messagebox.showerror("Save Error", f"Could not write file:\n{e}")


def main():
    app = JB7Converter()
    app.mainloop()


if __name__ == "__main__":
    main()
