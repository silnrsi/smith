/* GTK+ Vala Sample Code */
using GLib;
using Gtk;

public class Sample : Window {
        construct {
                title = "Sample Window";
                create_widgets ();
        }

        public void create_widgets () {
                destroy += Gtk.main_quit;

                var button = new Button.with_label ("Hello World");
                button.clicked += btn => {
                        title = btn.label;
                };

                add (button);
        }

        static int main (string[] args) {
                Gtk.init (ref args);

                var sample = new Sample ();
                sample.show_all ();

                Gtk.main ();
                return 0;
        }
}

