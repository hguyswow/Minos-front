// PC-side check of ra_settings.inc.  Build:  gcc -O0 -g -Wall -o test_ra_settings test_ra_settings.c
// Run:    ./test_ra_settings /path/to/pandory.xml
#include "ra_settings.inc"

static int fails;
#define EXPECT(folder, file, st, sm) do { Disp d; xml_display(xml, folder, file, &d); \
    int ok = !strcmp(d.stretch, st) && !strcmp(d.smooth, sm); \
    printf("%s  %-10s %-24s stretch='%s' smooth='%s'  (want '%s','%s')\n", ok ? "ok  " : "FAIL", folder, file, d.stretch, d.smooth, st, sm); \
    if (!ok) fails++; } while (0)

int main(int argc, char **argv) {
    const char *xml = argc > 1 ? argv[1] : "pandory.xml";
    // synthetic file written next to the real one
    const char *syn = "/tmp/ra_settings_syn.xml";
    FILE *f = fopen(syn, "w");
    fputs("<pandory>\n<system>\n"
          "  <setting name=\"stretchDisplay\" value=\"false\" />\n"
          "  <setting name=\"smoothPixels\" value=\"false\"/>\n"
          "</system>\n<emulators>\n"
          "  <emulator suffix=\"PICO\" folder=\"genesis\" core=\"picodrive\" />\n"
          "  <emulator suffix=\"GBLINK\" folder=\"gblink\" core=\"x\" stretchDisplay=\"true\" smoothPixels='true' />\n"
          "  <emulator suffix=\"GBA\" folder=\"gba\" core=\"mgba\" />\n"
          "</emulators>\n"
          "<!-- <rom name=\"decoy.zip\" stretchDisplay=\"true\" /> -->\n"
          "<roms>\n"
          "  <rom name=\"a.zip\" stretchDisplay=\"true\" speed=\"100\" />\n"
          "  <rom name='single.zip' smoothPixels='true'/>\n"
          "  <rom name=\"gt.zip\" note=\"a>b stretchDisplay=\\\"true\\\"\" />\n"
          "  <rom name=\"xmen.zip\" keymap=\"fbae-xmen\"core=\"fba-external\" stretchDisplay=\"true\" />\n"
          "</roms>\n</pandory>\n", f);
    fclose(f);
    xml = syn;
    EXPECT("genesis", "none.zip", "false", "false");   // global only
    EXPECT("gblink", "none.zip", "true", "true");      // emulator beats global
    EXPECT("gba", "a.zip", "true", "false");           // rom beats emulator/global; smooth falls through
    EXPECT("gblink", "a.zip", "true", "true");
    EXPECT("gba", "single.zip", "false", "true");      // single quotes
    EXPECT("gba", "decoy.zip", "false", "false");      // commented out
    EXPECT("gba", "gt.zip", "false", "false");         // '>' and look-alike text inside another attribute
    EXPECT("gba", "xmen.zip", "true", "false");        // the card's real malformed line is still readable
    if (argc > 1) {                                    // the real card file
        xml = argv[1];
        Disp d;
        xml_display(xml, "genesis", "Sonic.zip", &d);   printf("real: genesis/Sonic.zip  stretch='%s' smooth='%s'\n", d.stretch, d.smooth);
        xml_display(xml, "gblink", "x.zip", &d);        printf("real: gblink/x.zip       stretch='%s' smooth='%s'  (card sets gblink to true)\n", d.stretch, d.smooth);
        xml_display(xml, "genesis", "xmen.zip", &d);    printf("real: genesis/xmen.zip   stretch='%s' smooth='%s'\n", d.stretch, d.smooth);
        xml_display(xml, "amiga", "none.zip", &d);      printf("real: amiga/none.zip     stretch='%s' smooth='%s'\n", d.stretch, d.smooth);
        Disp w = {"true", "false"}; write_ra_override("/tmp/ra_override_test.cfg", &w, 0);
        { FILE *l = fopen("/tmp/ra_layout_test.cfg", "w"); fputs("input_player1_a = \"f\"", l); fclose(l); }   // no trailing newline on purpose
        append_file("/tmp/ra_override_test.cfg", "/tmp/ra_layout_test.cfg"); append_file("/tmp/ra_override_test.cfg", "/tmp/does_not_exist.cfg");
        write_ra_override("/tmp/ra_skip_test.cfg", &w, 1);
        char b[200] = {0}; FILE *g = fopen("/tmp/ra_override_test.cfg", "r"); size_t k = fread(b, 1, sizeof b - 1, g); fclose(g); (void)k;
        printf("override file for (true,false):\n%s", b);
    }
    printf(fails ? "\n%d FAILED\n" : "\nall ok\n", fails);
    return fails != 0;
}
