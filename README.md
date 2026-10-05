# Bikram Sambat

An [Omarchy](https://omarchy.org) bar plugin for Nepal's civil calendar. The bar shows today's Bikram Sambat date. Click it for the month, with government holidays marked.

The clock stays where it is. File timestamps, git, browsers, and the rest of the machine keep Gregorian dates. This widget is the date choice.

* **BS** shows the Bikram date, for example `असोज १९`.
* **Both** shows `असोज १९ · 5 Oct`. This is the default.
* **AD** shows the Gregorian date on this widget.

Pick one in the panel. The choice is stored on this widget. Install does not change the clock, the locale, or any other setting.

Saturday is marked as the weekly off from the 2083 notice. A dot is a government holiday. The line under the grid names who it applies to when it is not nationwide. Eid and the other days the notice left undated are omitted.

## Install

```sh
omarchy plugin add https://github.com/ashiskharel/omarchy-bikram.git --enable --yes
```

That puts it in the center of the bar, beside the clock. Move it:

```sh
omarchy bar put ashis.bikram --after omarchy.clock
```

## Remove

```sh
omarchy plugin remove ashis.bikram
```

That disables the plugin and deletes the installed copy. The rest of the bar stays as it is.

## Dates and holidays

Conversion uses a vendored month-length table for Bikram Sambat 1975 through 2100. Nepal's civil months run 29 to 32 days, so the table is the calendar. The month grid reads the system clock and the files shipped with the plugin.

The 2083 holiday list is the Ministry of Home Affairs notice for that year. Each included day was checked so the Bikram Sambat date and the Gregorian date in that notice are the same day. Days the notice left undated are omitted. A later year needs a new reviewed file in `holidays/`.

Once a month, opening the panel reads one page on moha.gov.np, the holiday page for the current Bikram Sambat year. The read is HTTPS, stays on that host, refuses a compressed body, and stops at 256 KiB or 15 seconds. The page is not saved. The plugin keeps the posted file's name, size, and upload id, and compares them with the reviewed list. It does not download the PDF. If that file changes, the panel says so and continues to show the reviewed list until the list itself is updated. If the page cannot be read, the reviewed list stays in use.

## License

The plugin is MIT. See `LICENSE`.

The month-length table in `vendor/calendar_bs.csv` is from [nepali-datetime](https://github.com/amitgaru/nepali-datetime) by Amit Garu, under the Apache License 2.0. See `vendor/APACHE-2.0.txt` and `vendor/NOTICE.md`. There are no other dependencies. The program uses the Python 3 that already ships with Omarchy.
