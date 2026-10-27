using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
[assembly: AssemblyTitle("CodexBar Desktop")]
[assembly: AssemblyProduct("CodexBar Desktop")]
[assembly: AssemblyDescription("Local Codex usage compatibility launcher")]
[assembly: AssemblyVersion("0.70.0.1")]
[assembly: AssemblyFileVersion("0.70.0.1")]
class Launcher {
    [STAThread] static void Main() {
        try {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string script = Path.Combine(local, "CodexBar", "usage-compat", "compat.py");
            string python = Path.Combine(local, "Programs", "Python", "Python312", "pythonw.exe");
            var info = new ProcessStartInfo(python, "\"" + script + "\" --launch");
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            Process.Start(info);
        } catch(Exception error) {
            MessageBox.Show(error.Message, "CodexBar", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
