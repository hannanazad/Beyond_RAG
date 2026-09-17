"""Table 6P-1 — Index to Typical Applications (2 sheets)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Table, Value as V

SRC = "vlm transcription from a PDF render, unverified"
T = []

# Group headings carry the governing SECTION ("see Section 6N.09"), which is
# how a verifier gets from a typical application back to the provisions that
# authorise it. Carried as its own column so every row keeps it.
def _6p1(n, page, rows):
    return Table(
        table_id="Table 6P-1", sheet=n, sheet_of=2, page_pdf=page, page_printed=str(page),
        title="Index to Typical Applications",
        crop_file=f"table_6P-1_s{n}_p{page:04d}.png", kind="text",
        column_labels=["Work Category", "Governing Section",
                       "Typical Application Description", "Typical Application Number"],
        row_key_columns=[3], source=SRC, note_chunk_ids=[],
        rows=[[V(text=g), V(text=sec), V(text=d), V(text=ta)]
              for g, sec, d, ta in rows],
    )

_S1 = [
 ("Work Outside of the Shoulder","6N.05","Work Beyond the Shoulder","TA-1"),
 ("Work Outside of the Shoulder","6N.05","Blasting Zone","TA-2"),
 ("Work on the Shoulder","6N.06, 6N.07","Work on the Shoulders","TA-3"),
 ("Work on the Shoulder","6N.06, 6N.07","Short-Duration or Mobile Operation on a Shoulder","TA-4"),
 ("Work on the Shoulder","6N.06, 6N.07","Shoulder Closure on a Freeway","TA-5"),
 ("Work on the Shoulder","6N.06, 6N.07","Shoulder Work with Minor Encroachment","TA-6"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Road Closed with a Diversion","TA-7"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Roads Closed with an Off-Site Detour","TA-8"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Overlapping Routes with a Detour","TA-9"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Lane Closure on a Two-Lane Road Using Flaggers","TA-10"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Lane Closure on a Two-Lane Road with Low Traffic Volumes","TA-11"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Lane Closure on a Two-Lane Road Using Traffic Control Signals","TA-12"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Temporary Road Closure","TA-13"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Haul Road Crossing","TA-14"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Work in the Center of a Road with Low Traffic Volumes","TA-15"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Surveying Along the Center Line of a Road with Low Traffic Volumes","TA-16"),
 ("Work within the Traveled Way of a Two-Lane Highway","6N.09","Mobile Operations on a Two-Lane Road","TA-17"),
 ("Work within the Traveled Way of an Urban Street","6N.10","Lane Closure on a Minor Street","TA-18"),
 ("Work within the Traveled Way of an Urban Street","6N.10","Detour for One Travel Direction","TA-19"),
 ("Work within the Traveled Way of an Urban Street","6N.10","Detour for a Closed Street","TA-20"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Lane Closure on the Near Side of an Intersection","TA-21"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Right-Hand Lane Closure on the Far Side of an Intersection","TA-22"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Left-Hand Lane Closure on the Far Side of an Intersection","TA-23"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Half Road Closure on the Far Side of an Intersection","TA-24"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Multiple Lane Closures at an Intersection","TA-25"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Closure in the Center of an Intersection","TA-26"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Closure at the Side of an Intersection","TA-27"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Sidewalk Detour or Diversion","TA-28"),
 ("Work within the Traveled Way at an Intersection and on Sidewalks","6N.12","Crosswalk Closures and Pedestrian Detours","TA-29"),
 ("Work within the Traveled Way of a Multi-Lane, Non-Access Controlled Highway","6N.11","Interior Lane Closure on a Multi-Lane Street","TA-30"),
 ("Work within the Traveled Way of a Multi-Lane, Non-Access Controlled Highway","6N.11","Lane Closure on a Street with Uneven Directional Volumes","TA-31"),
 ("Work within the Traveled Way of a Multi-Lane, Non-Access Controlled Highway","6N.11","Half Road Closure on a Multi-Lane, High-Speed Highway","TA-32"),
 ("Work within the Traveled Way of a Multi-Lane, Non-Access Controlled Highway","6N.11","Stationary Lane Closure on a Divided Highway","TA-33"),
 ("Work within the Traveled Way of a Multi-Lane, Non-Access Controlled Highway","6N.11","Lane Closure with a Temporary Traffic Barrier","TA-34"),
 ("Work within the Traveled Way of a Multi-Lane, Non-Access Controlled Highway","6N.11","Mobile Operation on a Multi-Lane Road","TA-35"),
]

_S2 = [
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Lane Shift on a Freeway","TA-36"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Double Lane Closure on a Freeway","TA-37"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Interior Lane Closure on a Freeway","TA-38"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Median Crossover on a Freeway","TA-39"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Median Crossover for an Entrance Ramp","TA-40"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Median Crossover for an Exit Ramp","TA-41"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Work in the Vicinity of an Exit Ramp","TA-42"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Partial Exit Ramp Closure","TA-43"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Work in the Vicinity of an Entrance Ramp","TA-44"),
 ("Work within the Traveled Way of a Freeway or Expressway","6N.13","Temporary Reversible Lane Using Movable Barriers","TA-45"),
 ("Work in the Vicinity of a Grade Crossing","6N.17","Work in the Vicinity of a Grade Crossing","TA-46"),
 ("Work in the Vicinity of Bicycle Lanes and Shared Use Paths","6N.04","Bicycle Lane Closure without a Detour","TA-47"),
 ("Work in the Vicinity of Bicycle Lanes and Shared Use Paths","6N.04","Bicycle Lane Closure with an On-Road Detour","TA-48"),
 ("Work in the Vicinity of Bicycle Lanes and Shared Use Paths","6N.04","Shared-Use Path Closure with a Diversion","TA-49"),
 ("Work in the Vicinity of Bicycle Lanes and Shared Use Paths","6N.04","On-Road Detour for a Shared-Use Path","TA-50"),
 ("Work in the Vicinity of Bicycle Lanes and Shared Use Paths","6N.04","Paved Shoulder Closure with a Bicycle Diversion onto a Temporary Path","TA-51"),
 ("Work in the Traveled Way of Roundabouts","","Short-Term or Short-Duration Work in a Circular Intersection","TA-52"),
 ("Work in the Traveled Way of Roundabouts","","Flagging Operation on a Single-Lane Circular Intersection","TA-53"),
 ("Work in the Traveled Way of Roundabouts","","Inside Lane Closure on a Multi-Lane Circular Intersection","TA-54"),
]

T.append(_6p1(1, 899, _S1))
T.append(_6p1(2, 900, _S2))
