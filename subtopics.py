"""Tag every question with sub-topics within its major topic.

Reads all_questions_classified.jsonl and writes a new field `subtopics`
(list[str], ranked by keyword score). The first entry is the primary
sub-topic. Writes back to the same file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
IN = ROOT / "all_questions_classified.jsonl"
OUT = ROOT / "all_questions_classified.jsonl"  # in-place

# ---------- subtopic keyword lists ----------
# Each sub-topic has (display_name, [keywords]). Keywords are matched as
# whole-word, case-insensitive, with optional trailing 's'.

SUBTOPICS: dict[str, list[tuple[str, list[str]]]] = {
    "Math": [
        ("Algebra & Equations", [
            "equation","inequality","variable","solve for","polynomial","quadratic",
            "linear","expression","term","coefficient","function","evaluate","simplify",
            "exponent","logarithm","square root","cube root","factor","factoring",
            "system of equations","substitute"]),
        ("Arithmetic & Operations", [
            "sum","product","difference","quotient","divide","multiply","add","subtract",
            "fraction","decimal","percent","percentage","ratio","proportion","unit rate",
            "order of operations","mixed number","reciprocal"]),
        ("Number Theory", [
            "integer","whole number","natural number","rational","irrational","prime",
            "composite","divisor","dividend","remainder","multiple","lcm","gcf","gcd",
            "factorial","sequence","fibonacci","arithmetic sequence","geometric sequence",
            "base-10","binary"]),
        ("Geometry (2D)", [
            "angle","degree","radian","triangle","right triangle","isosceles",
            "equilateral","scalene","hypotenuse","pythagorean","parallelogram","rhombus",
            "trapezoid","quadrilateral","pentagon","hexagon","octagon","polygon",
            "square","rectangle","circle","radius","diameter","circumference","arc",
            "chord","pi","area","perimeter","interior angle","exterior angle"]),
        ("Solid Geometry (3D)", [
            "cube","sphere","cylinder","cone","pyramid","prism","tetrahedron",
            "polyhedron","volume","surface area","face","edge","vertex"]),
        ("Coordinate Geometry", [
            "slope","intercept","graph","coordinate","origin","x-axis","y-axis",
            "ordered pair","quadrant","midpoint","distance formula"]),
        ("Probability & Statistics", [
            "mean","median","mode","range","standard deviation","probability",
            "permutation","combination","variance","expected value","odds",
            "data set","survey","sample"]),
        ("Measurement & Units", [
            "meter","centimeter","kilometer","liter","milliliter","gram","kilogram",
            "pound","ounce","mile","foot","inch","yard","gallon","quart","hour",
            "minute","second","convert","conversion"]),
    ],
    "Physics": [
        ("Mechanics (speed, velocity, acceleration)", [
            "velocity","acceleration","deceleration","displacement","momentum",
            "projectile","trajectory","kinematics","collision","elastic collision",
            "inelastic collision","meters per second","kilometers per hour",
            "miles per hour","average speed"]),
        ("Forces & Newton's Laws", [
            "force","newton","friction","gravity","gravitational","weight",
            "normal force","tension","free body","action","reaction","law of motion",
            "net force","equilibrium"]),
        ("Energy, Work & Power", [
            "kinetic energy","potential energy","mechanical energy","work","power",
            "joule","watt","horsepower","conservation of energy","energy transfer"]),
        ("Simple Machines", [
            "lever","pulley","inclined plane","wedge","screw","wheel and axle",
            "simple machine","mechanical advantage","fulcrum","effort","load"]),
        ("Fluids & Pressure", [
            "pressure","pascal","buoyancy","archimedes","hydraulic","pneumatic",
            "fluid","density","viscosity","atmospheric pressure","barometer"]),
        ("Heat & Thermodynamics", [
            "heat transfer","thermal","conduction","convection","specific heat",
            "calorie","celsius","kelvin","fahrenheit","thermometer","thermodynamics",
            "entropy","heat engine","carnot"]),
        ("States of Matter & Phase Change", [
            "state of matter","solid","liquid","gas","plasma","phase change",
            "melting point","boiling point","freezing point","sublimation",
            "condensation","evaporation","deposition"]),
        ("Electricity & Circuits", [
            "electric","electricity","charge","voltage","voltmeter","current","ampere",
            "ammeter","ohm","resistance","resistor","circuit","series","parallel",
            "capacitor","capacitance","insulator","conductor","semiconductor","battery",
            "coulomb"]),
        ("Magnetism & Electromagnetism", [
            "magnet","magnetic","magnetism","magnetic field","north pole","south pole",
            "compass","electromagnet","electromagnetic","induction","solenoid"]),
        ("Waves & Sound", [
            "wave","wavelength","frequency","amplitude","hertz","transverse",
            "longitudinal","medium","sound","pitch","decibel","doppler","echo",
            "resonance","vibration","standing wave"]),
        ("Light & Optics", [
            "light","photon","lens","mirror","reflection","refraction","prism",
            "spectrum","visible light","ultraviolet","infrared","laser","opaque",
            "translucent","transparent","focal","convex","concave","refractive index",
            "color"]),
        ("Nuclear & Modern Physics", [
            "nuclear","fission","fusion","radioactive","radioactivity","alpha",
            "beta particle","gamma ray","half-life","isotope","neutron","proton",
            "electron","quantum","atomic nucleus"]),
    ],
    "Chemistry": [
        ("Atomic Structure", [
            "atom","atomic","electron","proton","neutron","orbital","shell",
            "electron configuration","valence","nucleus (atom)","quantum number"]),
        ("Periodic Table & Elements", [
            "periodic table","group","period","alkali metal","alkaline earth",
            "halogen","noble gas","transition metal","metalloid","nonmetal",
            "lanthanide","actinide","atomic number","atomic mass"]),
        ("Chemical Bonding", [
            "ionic","covalent","metallic bond","bond","polar","nonpolar",
            "electronegativity","lewis structure","hybridization","vsepr"]),
        ("Chemical Reactions", [
            "reaction","reactant","product","catalyst","equilibrium","combustion",
            "synthesis","decomposition","single replacement","double replacement",
            "oxidation","reduction","redox","exothermic","endothermic","yield",
            "balanced equation"]),
        ("Stoichiometry & Moles", [
            "mole","molar","molarity","molality","stoichiometry","molecular formula",
            "empirical formula","avogadro","molar mass"]),
        ("Acids, Bases & pH", [
            "acid","acidic","alkaline","ph scale","buffer","hydroxide","titration",
            "indicator","litmus","phenolphthalein","neutralization"]),
        ("Solutions & Mixtures", [
            "solution","solute","solvent","concentration","dilute","dilution","mixture",
            "suspension","colloid","soluble","insoluble","solubility","precipitate",
            "crystallization"]),
        ("Gas Laws", [
            "boyle","charles","avogadro","gas law","ideal gas","stp","standard temperature",
            "partial pressure"]),
        ("Organic Chemistry", [
            "organic","inorganic","hydrocarbon","polymer","monomer","alkane","alkene",
            "alkyne","benzene","ester","ether","alcohol","amine","aldehyde","ketone",
            "carboxyl","hydroxyl","functional group","isomer"]),
        ("Element & Compound ID", [
            "hydrogen","helium","lithium","beryllium","boron","carbon","nitrogen",
            "oxygen","fluorine","neon","sodium","magnesium","aluminum","silicon",
            "phosphorus","sulfur","chlorine","argon","potassium","calcium","iron",
            "copper","zinc","silver","gold","tin","lead","mercury","bromine","iodine",
            "nickel","chromium","manganese","cobalt","titanium","platinum","uranium",
            "oxide","peroxide","hydride","chloride","sulfate","nitrate","carbonate",
            "phosphate","ammonia","ammonium"]),
    ],
    "Life Sciences": [
        ("Cell Biology", [
            "cell","organelle","nucleus","nuclei","ribosome","mitochondrion",
            "mitochondria","chloroplast","cytoplasm","membrane","vacuole","lysosome",
            "golgi","endoplasmic","cell wall","cytoskeleton","prokaryote","eukaryote"]),
        ("Genetics & Heredity", [
            "dna","rna","gene","chromosome","allele","genotype","phenotype","genetic",
            "heredity","mutation","dominant","recessive","homozygous","heterozygous",
            "mendel","pedigree","trait","punnett","genetic code","transcription",
            "translation","codon"]),
        ("Human Anatomy & Physiology", [
            "organ","tissue","muscle","bone","skeleton","heart","lung","kidney","liver",
            "stomach","intestine","brain","nerve","neuron","blood","artery","vein",
            "capillary","hemoglobin","plasma","platelet","alveoli","villi","pancreas",
            "spleen","thyroid","respiration","circulation","digestion","excretion",
            "nervous system","endocrine"]),
        ("Immunity & Disease", [
            "immune","antibody","antigen","vaccine","pathogen","disease","cancer",
            "tumor","diabetes","asthma","allergy","inflammation","white blood cell",
            "lymphocyte","virus","bacterium","bacteria","infection"]),
        ("Plants & Botany", [
            "plant","stem","root","leaf","leaves","xylem","phloem","flower","pollination",
            "seed","germination","angiosperm","gymnosperm","moss","fern","algae",
            "chlorophyll","photosynthesis","transpiration","meristem"]),
        ("Animal Kingdom & Classification", [
            "mammal","reptile","amphibian","bird","fish","insect","arthropod","mollusk",
            "vertebrate","invertebrate","chordate","arachnid","crustacean","species",
            "genus","family","phylum","kingdom","domain","taxonomy","binomial"]),
        ("Microbiology", [
            "fungus","protist","archaea","microbe","microorganism","yeast","mold"]),
        ("Ecology & Ecosystems", [
            "ecosystem","food chain","food web","predator","prey","producer","consumer",
            "decomposer","biome","habitat","niche","symbiosis","parasite","mutualism",
            "commensalism","population","community","trophic"]),
        ("Evolution & Adaptation", [
            "evolution","natural selection","darwin","adaptation","speciation","fossil",
            "common ancestor","divergence"]),
        ("Reproduction & Development", [
            "mitosis","meiosis","cell division","fertilization","zygote","embryo",
            "gamete","sperm","egg","ovary","testis","uterus","placenta","gestation"]),
        ("Biochemistry & Molecules", [
            "enzyme","protein","amino acid","carbohydrate","lipid","nucleic acid",
            "peptide","hormone","insulin","adrenaline","glucose","atp","metabolism",
            "homeostasis","osmosis","diffusion","active transport"]),
    ],
    "Earth and Space": [
        ("Astronomy & Universe", [
            "galaxy","nebula","supernova","black hole","pulsar","quasar","universe",
            "big bang","redshift","constellation","light year","parsec","astronomical unit",
            "cosmic","interstellar"]),
        ("Solar System", [
            "sun","mercury","venus","earth","mars","jupiter","saturn","uranus",
            "neptune","pluto","dwarf planet","planet","moon","satellite","asteroid",
            "comet","meteor","meteorite","meteoroid","solar system","orbit","revolution",
            "rotation","axis","tilt","eclipse","equinox","solstice","phases of the moon"]),
        ("Space Exploration", [
            "nasa","hubble","telescope","observatory","spacecraft","astronaut","iss",
            "international space station","rover","probe"]),
        ("Geology & Rocks", [
            "rock","mineral","ore","gem","igneous","sedimentary","metamorphic",
            "geology","lithosphere","basalt","granite","limestone","sandstone","shale",
            "crystal lattice","mohs"]),
        ("Plate Tectonics & Earthquakes", [
            "volcano","volcanic","lava","magma","eruption","caldera","hotspot",
            "earthquake","seismic","seismograph","fault","richter","epicenter",
            "aftershock","tectonic","continental drift","pangaea","plate","subduction",
            "rift","mid-ocean ridge"]),
        ("Atmosphere & Climate", [
            "atmosphere","troposphere","stratosphere","mesosphere","thermosphere",
            "ionosphere","ozone","climate","greenhouse effect","global warming"]),
        ("Weather & Meteorology", [
            "weather","humidity","precipitation","rain","snow","hail","sleet","blizzard",
            "hurricane","typhoon","tornado","cyclone","thunderstorm","lightning",
            "front","air mass","high pressure","low pressure","barometer","meteorology",
            "meteorologist"]),
        ("Oceanography & Hydrology", [
            "ocean","sea","current","tide","tidal","tsunami","salinity","coastal",
            "estuary","reef","wave (ocean)","river","watershed","aquifer"]),
        ("Earth Features & Processes", [
            "erosion","weathering","deposition","sediment","glacier","iceberg","delta",
            "moraine","canyon","valley","mountain","plateau","desert","tundra",
            "rainforest","savanna","taiga","grassland","wetland"]),
        ("Paleontology & Earth History", [
            "fossil","era","period","epoch","paleozoic","mesozoic","cenozoic",
            "jurassic","cretaceous","triassic","cambrian","devonian","carboniferous",
            "permian","dinosaur","mass extinction"]),
        ("Earth Measurement & Mapping", [
            "longitude","latitude","equator","hemisphere","tropic","meridian","pole",
            "elevation","altitude","topographic"]),
    ],
    "Energy": [
        ("Fossil Fuels", [
            "fossil fuel","coal","petroleum","crude oil","natural gas","shale",
            "oil refinery","drilling","fracking"]),
        ("Renewable Energy — Solar", [
            "solar panel","photovoltaic","solar cell","solar energy","solar thermal",
            "concentrated solar"]),
        ("Renewable Energy — Wind", [
            "wind turbine","wind farm","wind energy","wind power"]),
        ("Renewable Energy — Water", [
            "hydroelectric","hydropower","tidal energy","wave energy","dam","turbine"]),
        ("Renewable Energy — Other", [
            "geothermal","geothermal energy","biomass","biofuel","biodiesel","ethanol",
            "wood pellet"]),
        ("Nuclear Energy", [
            "nuclear power","nuclear reactor","nuclear plant","reactor core","uranium",
            "nuclear fission","nuclear fusion"]),
        ("Electrical Grid & Storage", [
            "grid","transmission line","generator","dynamo","battery","fuel cell",
            "lithium-ion","lead acid","smart grid","power consumption","load",
            "peak demand","kilowatt","kilowatt-hour","megawatt","gigawatt"]),
        ("Energy Efficiency & Conservation", [
            "efficiency","energy conservation","insulation","energy star",
            "energy efficiency","fuel economy","mpg","led","compact fluorescent"]),
        ("Climate & Environment", [
            "climate change","global warming","carbon footprint","greenhouse gas",
            "greenhouse effect","emissions","carbon emissions","carbon dioxide emissions",
            "cap and trade","carbon tax","renewable portfolio","clean energy",
            "green energy"]),
        ("Energy Agencies & Policy", [
            "department of energy","doe","eia","oak ridge","argonne","lawrence livermore",
            "fermilab","energy policy","energy information administration"]),
    ],
}


def compile_subtopics():
    out: dict[str, list[tuple[str, list[re.Pattern]]]] = {}
    for topic, buckets in SUBTOPICS.items():
        out[topic] = []
        for name, terms in buckets:
            pats = [re.compile(r"\b" + re.escape(t) + r"s?\b", re.IGNORECASE) for t in terms]
            out[topic].append((name, pats))
    return out


COMPILED = compile_subtopics()

# split off multiple-choice options from question stem
CHOICE_RE = re.compile(r"\n\s*[WXYZ]\)", re.IGNORECASE)


def tag_subtopics(topic: str, question: str, answer: str) -> list[str]:
    """Return subtopics (ordered by descending match score) for a question."""
    buckets = COMPILED.get(topic)
    if not buckets:
        return []

    m = CHOICE_RE.search(question)
    stem = question[: m.start()] if m else question
    rest = (question[m.start():] if m else "") + " " + answer

    scored = []
    for name, pats in buckets:
        s_stem = sum(1 for p in pats if p.search(stem))
        s_rest = sum(1 for p in pats if p.search(rest))
        score = s_stem * 3 + s_rest  # weight stem heavier, same as topic classifier
        if score > 0:
            scored.append((score, name))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [n for _, n in scored]


def main():
    rows = []
    for line in IN.open():
        r = json.loads(line)
        r["subtopics"] = tag_subtopics(r.get("topic6", r["topic"]), r["question"], r["answer"])
        r["subtopic"] = r["subtopics"][0] if r["subtopics"] else "Other / General"
        rows.append(r)

    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Summary
    from collections import Counter, defaultdict
    print(f"Tagged {len(rows)} questions")
    by_topic: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_topic[r.get("topic6", r["topic"])][r["subtopic"]] += 1

    for topic in ["Math","Physics","Chemistry","Life Sciences","Earth and Space","Energy"]:
        c = by_topic[topic]
        print(f"\n{topic}  ({sum(c.values())} total)")
        for sub, n in c.most_common():
            print(f"  {sub:50s} {n:>5}")


if __name__ == "__main__":
    main()
