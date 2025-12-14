import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os

# reuse pick_nearest from pick_nearest_speed.py
from pick_nearest_speed import pick_nearest


class PickNearestGUI:
    def __init__(self, root):
        self.root = root
        root.title('Pick Nearest Speed — Table View')

        frm = tk.Frame(root)
        frm.pack(padx=8, pady=8, fill='x')

        tk.Label(frm, text='OHE CSV:').grid(row=0, column=0, sticky='w')
        self.ohe_entry = tk.Entry(frm, width=60)
        self.ohe_entry.grid(row=0, column=1, padx=4)
        tk.Button(frm, text='Browse', command=self.browse_ohe).grid(row=0, column=2)

        tk.Label(frm, text='RTIS CSV:').grid(row=1, column=0, sticky='w')
        self.rtis_entry = tk.Entry(frm, width=60)
        self.rtis_entry.grid(row=1, column=1, padx=4)
        tk.Button(frm, text='Browse', command=self.browse_rtis).grid(row=1, column=2)

        tk.Label(frm, text='Max distance (m):').grid(row=2, column=0, sticky='w')
        self.maxdist = tk.Entry(frm, width=10)
        self.maxdist.insert(0, '50')
        self.maxdist.grid(row=2, column=1, sticky='w')

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill='x', padx=8, pady=(0,6))
        tk.Button(btn_frame, text='Run', command=self.run).pack(side='left')
        tk.Button(btn_frame, text='Save CSV', command=self.save_csv).pack(side='left', padx=6)

        search_frame = tk.Frame(root)
        search_frame.pack(fill='x', padx=8)
        tk.Label(search_frame, text='Search OHEMas:').pack(side='left')
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self.filter_table())
        tk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side='left', padx=6)
        tk.Button(search_frame, text='Find', command=self.find_pole).pack(side='left', padx=4)

        # Treeview for results
        cols = ('OHEMas', 'logging_time', 'speed_kmph')
        self.tree = ttk.Treeview(root, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=150)
        self.tree.pack(fill='both', expand=1, padx=8, pady=8)

        self.df = pd.DataFrame(columns=cols)

    def browse_ohe(self):
        p = filedialog.askopenfilename(filetypes=[('CSV', '*.csv')])
        if p:
            self.ohe_entry.delete(0, tk.END)
            self.ohe_entry.insert(0, p)

    def browse_rtis(self):
        p = filedialog.askopenfilename(filetypes=[('CSV', '*.csv')])
        if p:
            self.rtis_entry.delete(0, tk.END)
            self.rtis_entry.insert(0, p)

    def run(self):
        ohe = self.ohe_entry.get().strip()
        rtis = self.rtis_entry.get().strip()
        if not ohe or not rtis:
            messagebox.showerror('Missing files', 'Please select both CSV files')
            return
        if not os.path.exists(ohe) or not os.path.exists(rtis):
            messagebox.showerror('Missing files', 'Selected files do not exist')
            return
        try:
            maxd = float(self.maxdist.get())
        except Exception:
            maxd = 50.0

        try:
            out_df = pick_nearest(ohe, rtis, out_csv='__tmp_output.csv', section=None, max_dist_m=maxd)
        except TypeError:
            # older pick_nearest signature may have section required; try with default
            out_df = pick_nearest(ohe, rtis, '__tmp_output.csv', max_dist_m=maxd)
        except SystemExit as e:
            messagebox.showerror('Error', str(e))
            return
        except Exception as e:
            messagebox.showerror('Error', str(e))
            return

        # pick_nearest writes out a CSV and also returns a DataFrame
        if isinstance(out_df, pd.DataFrame):
            self.df = out_df.copy()
        else:
            # fallback: read the temporary CSV
            try:
                self.df = pd.read_csv('__tmp_output.csv')
            except Exception as e:
                messagebox.showerror('Error', f'Could not read output: {e}')
                return

        # remove any distance column if present
        if 'distance_m' in self.df.columns:
            self.df = self.df.drop(columns=['distance_m'])

        self.populate_table(self.df)

    def populate_table(self, df):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for _, row in df.iterrows():
            self.tree.insert('', 'end', values=(row.get('OHEMas',''), row.get('logging_time',''), row.get('speed_kmph','')))

    def find_pole(self):
        q = self.search_var.get().strip().lower()
        if q == '':
            return
        # Search the visible tree rows first
        for item in self.tree.get_children():
            vals = self.tree.item(item).get('values', [])
            if vals and q in str(vals[0]).lower():
                self.tree.selection_set(item)
                self.tree.see(item)
                return
        # If not found in visible rows, try in full dataframe and repopulate table
        matches = self.df[self.df['OHEMas'].astype(str).str.lower().str.contains(q)]
        if not matches.empty:
            self.populate_table(matches)
            # select first
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.see(first)
            return
        messagebox.showinfo('Not found', f'No matching pole for "{q}"')

    def filter_table(self):
        q = self.search_var.get().strip().lower()
        if q == '':
            df = self.df
        else:
            df = self.df[self.df['OHEMas'].astype(str).str.lower().str.contains(q)]
        self.populate_table(df)

    def save_csv(self):
        if self.df is None or self.df.empty:
            messagebox.showinfo('No data', 'No data to save')
            return
        p = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if not p:
            return
        self.df.to_csv(p, index=False)
        messagebox.showinfo('Saved', f'Saved {p}')


def main():
    root = tk.Tk()
    app = PickNearestGUI(root)
    root.geometry('800x600')
    root.mainloop()


if __name__ == '__main__':
    main()
