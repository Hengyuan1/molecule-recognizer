// Native Windows region selection. All desktop/crop pixels stay in memory.
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public sealed class MolRecognizerCapture : Form {
    [DllImport("user32.dll")]
    private static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")]
    private static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")]
    private static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")]
    private static extern uint GetDpiForWindow(IntPtr window);

    private readonly Bitmap desktop;
    private Rectangle selection = Rectangle.Empty;
    private Rectangle original;
    private Point origin;
    private int drag; // 1=left, 2=right, 4=top, 8=bottom, 16=move, 32=draw
    private float ui = 1;
    public string Result = "CANCEL";

    public static Rectangle SelectionBounds(Point a, Point b, Size size) {
        return Rectangle.FromLTRB(
            Math.Max(0, Math.Min(a.X, b.X)), Math.Max(0, Math.Min(a.Y, b.Y)),
            Math.Min(size.Width, Math.Max(a.X, b.X)),
            Math.Min(size.Height, Math.Max(a.Y, b.Y)));
    }

    public static Rectangle MoveRegion(Rectangle r, Point delta, Size size) {
        return new Rectangle(Math.Max(0, Math.Min(size.Width - r.Width, r.X + delta.X)),
                             Math.Max(0, Math.Min(size.Height - r.Height, r.Y + delta.Y)),
                             r.Width, r.Height);
    }

    public static string EncodeCrop(Bitmap image, Rectangle region) {
        using (Bitmap crop = image.Clone(region, PixelFormat.Format32bppArgb))
        using (MemoryStream bytes = new MemoryStream()) {
            crop.Save(bytes, ImageFormat.Png);
            return "PNG:" + Convert.ToBase64String(bytes.ToArray());
        }
    }

    public static string Run() {
        // Set before reading Screen.Bounds or taking a bitmap: both must use
        // physical pixels, including monitors with negative desktop origins.
        try {
            SetProcessDpiAwarenessContext(new IntPtr(-4));
            SetThreadDpiAwarenessContext(new IntPtr(-4));
        }
        catch (EntryPointNotFoundException) { SetProcessDPIAware(); }
        Rectangle bounds = Screen.FromPoint(Cursor.Position).Bounds;
        using (Bitmap image = new Bitmap(bounds.Width, bounds.Height, PixelFormat.Format32bppArgb)) {
            using (Graphics g = Graphics.FromImage(image))
                g.CopyFromScreen(bounds.Location, Point.Empty, bounds.Size, CopyPixelOperation.SourceCopy);
            using (MolRecognizerCapture overlay = new MolRecognizerCapture(image, bounds)) {
                overlay.ShowDialog();
                return overlay.Result;
            }
        }
    }

    public MolRecognizerCapture(Bitmap image, Rectangle bounds) {
        desktop = image;
        AutoScaleMode = AutoScaleMode.None;
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.Manual;
        Bounds = bounds;
        ShowInTaskbar = false;
        TopMost = true;
        DoubleBuffered = true;
        KeyPreview = true;
        Cursor = Cursors.Cross;
        Text = "Select structure region";
    }

    protected override void OnShown(EventArgs e) {
        base.OnShown(e);
        try { ui = Math.Max(1, Math.Min(2.5f, GetDpiForWindow(Handle) / 96f)); }
        catch (EntryPointNotFoundException) { ui = 1; }
        Font = new Font("Segoe UI", 14 * ui, FontStyle.Regular, GraphicsUnit.Pixel);
        Activate();
        Console.WriteLine("READY");
        Console.Out.Flush();
        Invalidate();
    }

    private int S(float value) { return (int)Math.Round(value * ui); }
    private Point Clamp(Point p) {
        return new Point(Math.Max(0, Math.Min(ClientSize.Width, p.X)),
                         Math.Max(0, Math.Min(ClientSize.Height, p.Y)));
    }
    private Rectangle Toolbar() {
        int width = S(216), height = S(36);
        int x = Math.Max(4, Math.Min(ClientSize.Width - width - 4, selection.Right - width));
        int y = selection.Bottom + S(10);
        if (y + height > ClientSize.Height) y = Math.Max(4, selection.Top - height - S(10));
        return new Rectangle(x, y, width, height);
    }
    private int Hit(Point p) {
        if (selection.Width < 3 || selection.Height < 3) return 0;
        Rectangle expanded = selection;
        expanded.Inflate(S(5), S(5));
        if (!expanded.Contains(p)) return 0;
        int edge = 0;
        if (Math.Abs(p.X - selection.Left) <= S(5)) edge |= 1;
        else if (Math.Abs(p.X - selection.Right) <= S(5)) edge |= 2;
        if (Math.Abs(p.Y - selection.Top) <= S(5)) edge |= 4;
        else if (Math.Abs(p.Y - selection.Bottom) <= S(5)) edge |= 8;
        return edge == 0 && selection.Contains(p) ? 16 : edge;
    }
    private void UpdateCursor(Point p) {
        int hit = Hit(p);
        if (selection.Width >= 3 && Toolbar().Contains(p)) Cursor = Cursors.Hand;
        else if (hit == 5 || hit == 10) Cursor = Cursors.SizeNWSE;
        else if (hit == 6 || hit == 9) Cursor = Cursors.SizeNESW;
        else if (hit == 1 || hit == 2) Cursor = Cursors.SizeWE;
        else if (hit == 4 || hit == 8) Cursor = Cursors.SizeNS;
        else if (hit == 16) Cursor = Cursors.SizeAll;
        else Cursor = Cursors.Cross;
    }

    protected override void OnPaint(PaintEventArgs e) {
        Graphics g = e.Graphics;
        g.DrawImageUnscaled(desktop, 0, 0);
        using (Brush dim = new SolidBrush(Color.FromArgb(100, 0, 0, 0))) {
            if (selection.Width < 3 || selection.Height < 3) g.FillRectangle(dim, ClientRectangle);
            else {
                g.FillRectangle(dim, 0, 0, ClientSize.Width, selection.Top);
                g.FillRectangle(dim, 0, selection.Bottom, ClientSize.Width, ClientSize.Height - selection.Bottom);
                g.FillRectangle(dim, 0, selection.Top, selection.Left, selection.Height);
                g.FillRectangle(dim, selection.Right, selection.Top, ClientSize.Width - selection.Right, selection.Height);
            }
        }
        using (Brush dark = new SolidBrush(Color.FromArgb(235, 25, 38, 52)))
        using (Brush blue = new SolidBrush(Color.FromArgb(50, 155, 255)))
        using (Pen border = new Pen(Color.FromArgb(50, 155, 255), Math.Max(1, S(1)))) {
            if (selection.Width >= 3 && selection.Height >= 3) {
                g.DrawRectangle(border, selection);
                int half = S(3);
                int[] xs = {selection.Left, selection.Left + selection.Width / 2, selection.Right};
                int[] ys = {selection.Top, selection.Top + selection.Height / 2, selection.Bottom};
                for (int x = 0; x < 3; x++) for (int y = 0; y < 3; y++)
                    if (x != 1 || y != 1) g.FillRectangle(blue, xs[x] - half, ys[y] - half, half * 2, half * 2);
                string size = selection.Width + " x " + selection.Height + " px";
                Rectangle label = new Rectangle(selection.Left, Math.Max(0, selection.Top - S(29)), S(170), S(25));
                g.FillRectangle(dark, label);
                TextRenderer.DrawText(g, size, Font, label, Color.White, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                if (drag == 0) {
                    Rectangle bar = Toolbar();
                    g.FillRectangle(dark, bar);
                    Rectangle ok = new Rectangle(bar.X + S(88), bar.Y, bar.Width - S(88), bar.Height);
                    g.FillRectangle(blue, ok);
                    TextRenderer.DrawText(g, "Cancel", Font, new Rectangle(bar.X, bar.Y, S(88), bar.Height), Color.White,
                                          TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                    TextRenderer.DrawText(g, "Recognize", Font, ok, Color.White,
                                          TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                }
            } else {
                Rectangle help = new Rectangle(S(20), S(20), Math.Min(ClientSize.Width - S(40), S(690)), S(44));
                g.FillRectangle(dark, help);
                TextRenderer.DrawText(g, "Drag to select a structure. Adjust the box, then Enter. Esc cancels.", Font, help,
                                      Color.White, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
            }
        }
    }

    protected override void OnMouseDown(MouseEventArgs e) {
        if (e.Button == MouseButtons.Right) { Close(); return; }
        if (e.Button != MouseButtons.Left) return;
        if (selection.Width >= 3 && Toolbar().Contains(e.Location)) {
            if (e.X < Toolbar().X + S(88)) Close(); else Confirm();
            return;
        }
        origin = Clamp(e.Location);
        original = selection;
        drag = Hit(origin);
        if (drag == 0) { drag = 32; selection = new Rectangle(origin, Size.Empty); }
        Capture = true;
        Invalidate();
    }
    protected override void OnMouseMove(MouseEventArgs e) {
        Point p = Clamp(e.Location);
        if (drag == 32) selection = SelectionBounds(origin, p, ClientSize);
        else if (drag == 16) selection = MoveRegion(original, new Point(p.X - origin.X, p.Y - origin.Y), ClientSize);
        else if (drag != 0) {
            int x1 = (drag & 1) != 0 ? original.Left + p.X - origin.X : original.Left;
            int x2 = (drag & 2) != 0 ? original.Right + p.X - origin.X : original.Right;
            int y1 = (drag & 4) != 0 ? original.Top + p.Y - origin.Y : original.Top;
            int y2 = (drag & 8) != 0 ? original.Bottom + p.Y - origin.Y : original.Bottom;
            selection = SelectionBounds(Clamp(new Point(x1, y1)), Clamp(new Point(x2, y2)), ClientSize);
        }
        UpdateCursor(p);
        if (drag != 0) Invalidate();
    }
    protected override void OnMouseUp(MouseEventArgs e) {
        if (e.Button != MouseButtons.Left) return;
        OnMouseMove(e);
        drag = 0;
        Capture = false;
        UpdateCursor(e.Location);
        Invalidate();
    }
    protected override void OnMouseCaptureChanged(EventArgs e) {
        base.OnMouseCaptureChanged(e);
        if (!Capture) { drag = 0; Invalidate(); }
    }
    protected override void OnKeyDown(KeyEventArgs e) {
        if (e.KeyCode == Keys.Escape) { Close(); e.Handled = true; }
        else if (e.KeyCode == Keys.Enter && drag == 0) { Confirm(); e.Handled = true; }
        else if (e.KeyCode == Keys.Left || e.KeyCode == Keys.Right || e.KeyCode == Keys.Up || e.KeyCode == Keys.Down) {
            int step = e.Shift ? 10 : 1;
            Point delta = new Point(e.KeyCode == Keys.Left ? -step : e.KeyCode == Keys.Right ? step : 0,
                                    e.KeyCode == Keys.Up ? -step : e.KeyCode == Keys.Down ? step : 0);
            selection = MoveRegion(selection, delta, ClientSize);
            Invalidate(); e.Handled = true;
        }
        base.OnKeyDown(e);
    }
    private void Confirm() {
        if (selection.Width < 3 || selection.Height < 3) return;
        // Crop the untouched original, never the dimmed/annotated overlay.
        Result = EncodeCrop(desktop, selection);
        Close();
    }
}
