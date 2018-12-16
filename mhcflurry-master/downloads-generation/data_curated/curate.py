"""
Filter and combine various peptide/MHC datasets to derive a composite training set,
optionally including eluted peptides identified by mass-spec.
"""
import sys
import argparse

import pandas

import mhcnames


def normalize_allele_name(s):
    try:
        return mhcnames.normalize_allele_name(s)
    except Exception:
        return "UNKNOWN"


parser = argparse.ArgumentParser(usage=__doc__)

parser.add_argument(
    "--data-kim2014",
    action="append",
    default=[],
    help="Path to Kim 2014-style affinity data")
parser.add_argument(
    "--data-iedb",
    action="append",
    default=[],
    help="Path to IEDB-style affinity data (e.g. mhc_ligand_full.csv)")
parser.add_argument(
    "--data-systemhc-atlas",
    action="append",
    default=[],
    help="Path to systemhc-atlas-style mass-spec data")
parser.add_argument(
    "--data-abelin-mass-spec",
    action="append",
    default=[],
    help="Path to Abelin Immunity 2017 mass-spec hits")
parser.add_argument(
    "--include-iedb-mass-spec",
    action="store_true",
    default=False,
    help="Include mass-spec observations in IEDB")

parser.add_argument(
    "--out-csv",
    required=True,
    help="Result file")

QUALITATIVE_TO_AFFINITY_AND_INEQUALITY = {
    "Negative": (5000.0, ">"),
    "Positive": (500.0, "<"),  # used for mass-spec hits
    "Positive-High": (100.0, "<"),
    "Positive-Intermediate": (1000.0, "<"),
    "Positive-Low": (5000.0, "<"),
}
QUALITATIVE_TO_AFFINITY = dict(
    (key, value[0]) for (key, value)
    in QUALITATIVE_TO_AFFINITY_AND_INEQUALITY.items())
QUALITATIVE_TO_INEQUALITY = dict(
    (key, value[1]) for (key, value)
    in QUALITATIVE_TO_AFFINITY_AND_INEQUALITY.items())


EXCLUDE_IEDB_ALLELES = [
    "HLA class I",
    "HLA class II",
]


def load_data_kim2014(filename):
    df = pandas.read_table(filename)
    print("Loaded kim2014 data: %s" % str(df.shape))
    df["measurement_source"] = "kim2014"
    df["measurement_value"] = df.meas
    df["measurement_type"] = (df.inequality == "=").map({
        True: "quantitative",
        False: "qualitative",
    })
    df["measurement_inequality"] = df.inequality
    df["original_allele"] = df.mhc
    df["peptide"] = df.sequence
    df["allele"] = df.mhc.map(normalize_allele_name)
    print("Dropping un-parseable alleles: %s" % ", ".join(
        df.ix[df.allele == "UNKNOWN"]["mhc"].unique()))
    df = df.ix[df.allele != "UNKNOWN"]

    print("Loaded kim2014 data: %s" % str(df.shape))
    return df


def load_data_systemhc_atlas(filename, min_probability=0.99):
    df = pandas.read_csv(filename)
    print("Loaded systemhc atlas data: %s" % str(df.shape))

    df["measurement_source"] = "systemhc-atlas"
    df["measurement_value"] = QUALITATIVE_TO_AFFINITY["Positive"]
    df["measurement_inequality"] = "<"
    df["measurement_type"] = "qualitative"
    df["original_allele"] = df.top_allele
    df["peptide"] = df.search_hit
    df["allele"] = df.top_allele.map(normalize_allele_name)

    print("Dropping un-parseable alleles: %s" % ", ".join(
        str(x) for x in df.ix[df.allele == "UNKNOWN"]["top_allele"].unique()))
    df = df.loc[df.allele != "UNKNOWN"]
    print("Systemhc atlas data now: %s" % str(df.shape))

    print("Dropping data points with probability < %f" % min_probability)
    df = df.loc[df.prob >= min_probability]
    print("Systemhc atlas data now: %s" % str(df.shape))

    print("Removing duplicates")
    df = df.drop_duplicates(["allele", "peptide"])
    print("Systemhc atlas data now: %s" % str(df.shape))

    return df


def load_data_abelin_mass_spec(filename):
    df = pandas.read_csv(filename)
    print("Loaded Abelin mass-spec data: %s" % str(df.shape))

    df["measurement_source"] = "abelin-mass-spec"
    df["measurement_value"] = QUALITATIVE_TO_AFFINITY["Positive"]
    df["measurement_inequality"] = "<"
    df["measurement_type"] = "qualitative"
    df["original_allele"] = df.allele
    df["allele"] = df.original_allele.map(normalize_allele_name)

    print("Dropping un-parseable alleles: %s" % ", ".join(
        str(x) for x in df.ix[df.allele == "UNKNOWN"]["allele"].unique()))
    df = df.loc[df.allele != "UNKNOWN"]
    print("Abelin mass-spec data now: %s" % str(df.shape))

    print("Removing duplicates")
    df = df.drop_duplicates(["allele", "peptide"])
    print("Abelin mass-spec data now: %s" % str(df.shape))

    return df


def load_data_iedb(iedb_csv, include_qualitative=True, include_mass_spec=False):
    iedb_df = pandas.read_csv(iedb_csv, skiprows=1, low_memory=False)
    print("Loaded iedb data: %s" % str(iedb_df.shape))

    print("Selecting only class I")
    iedb_df = iedb_df.ix[
        iedb_df["MHC allele class"].str.strip().str.upper() == "I"
    ]
    print("New shape: %s" % str(iedb_df.shape))

    print("Dropping known unusuable alleles")
    iedb_df = iedb_df.ix[
        ~iedb_df["Allele Name"].isin(EXCLUDE_IEDB_ALLELES)
    ]
    iedb_df = iedb_df.ix[
        (~iedb_df["Allele Name"].str.contains("mutant")) &
        (~iedb_df["Allele Name"].str.contains("CD1"))
    ]

    iedb_df["allele"] = iedb_df["Allele Name"].map(normalize_allele_name)
    print("Dropping un-parseable alleles: %s" % ", ".join(
        iedb_df.ix[iedb_df.allele == "UNKNOWN"]["Allele Name"].unique()))
    iedb_df = iedb_df.ix[iedb_df.allele != "UNKNOWN"]

    print("IEDB measurements per allele:\n%s" % iedb_df.allele.value_counts())

    quantitative = iedb_df.ix[iedb_df["Units"] == "nM"].copy()
    quantitative["measurement_type"] = "quantitative"
    quantitative["measurement_inequality"] = "="
    print("Quantitative measurements: %d" % len(quantitative))

    qualitative = iedb_df.ix[iedb_df["Units"] != "nM"].copy()
    qualitative["measurement_type"] = "qualitative"
    print("Qualitative measurements: %d" % len(qualitative))
    if not include_mass_spec:
        qualitative = qualitative.ix[
            (~qualitative["Method/Technique"].str.contains("mass spec"))
        ].copy()

    qualitative["Quantitative measurement"] = (
        qualitative["Qualitative Measure"].map(QUALITATIVE_TO_AFFINITY))
    qualitative["measurement_inequality"] = (
        qualitative["Qualitative Measure"].map(QUALITATIVE_TO_INEQUALITY))

    print("Qualitative measurements (possibly after dropping MS): %d" % (
        len(qualitative)))

    iedb_df = pandas.concat(
        (
            ([quantitative]) +
            ([qualitative] if include_qualitative else [])),
        ignore_index=True)

    print("IEDB measurements per allele:\n%s" % iedb_df.allele.value_counts())

    print("Subselecting to valid peptides. Starting with: %d" % len(iedb_df))
    iedb_df["Description"] = iedb_df.Description.str.strip()
    iedb_df = iedb_df.ix[
        iedb_df.Description.str.match("^[ACDEFGHIKLMNPQRSTVWY]+$")
    ]
    print("Now: %d" % len(iedb_df))

    print("Annotating last author and category")
    iedb_df["last_author"] = iedb_df.Authors.map(
        lambda x: (
            x.split(";")[-1]
            .split(",")[-1]
            .split(" ")[-1]
            .strip()
            .replace("*", ""))).values
    iedb_df["category"] = (
        iedb_df["last_author"] + " - " + iedb_df["Method/Technique"]).values

    train_data = pandas.DataFrame()
    train_data["peptide"] = iedb_df.Description.values
    train_data["measurement_value"] = iedb_df[
        "Quantitative measurement"
    ].values
    train_data["measurement_source"] = iedb_df.category.values
    train_data["measurement_inequality"] = iedb_df.measurement_inequality.values

    train_data["allele"] = iedb_df["allele"].values
    train_data["original_allele"] = iedb_df["Allele Name"].values
    train_data["measurement_type"] = iedb_df["measurement_type"].values
    train_data = train_data.drop_duplicates().reset_index(drop=True)

    return train_data


def run():
    args = parser.parse_args(sys.argv[1:])

    dfs = []
    for filename in args.data_iedb:
        df = load_data_iedb(filename, include_mass_spec=args.include_iedb_mass_spec)
        dfs.append(df)
    for filename in args.data_kim2014:
        df = load_data_kim2014(filename)
        df["allele_peptide"] = df.allele + "_" + df.peptide

        # Give precedence to IEDB data.
        if dfs:
            iedb_df = dfs[0]
            iedb_df["allele_peptide"] = iedb_df.allele + "_" + iedb_df.peptide
            print("Dropping kim2014 data present in IEDB.")
            df = df.ix[
                ~df.allele_peptide.isin(iedb_df.allele_peptide)
            ]
            print("Kim2014 data now: %s" % str(df.shape))
        dfs.append(df)
    for filename in args.data_systemhc_atlas:
        df = load_data_systemhc_atlas(filename)
        dfs.append(df)
    for filename in args.data_abelin_mass_spec:
        df = load_data_abelin_mass_spec(filename)
        dfs.append(df)

    df = pandas.concat(dfs, ignore_index=True)
    print("Combined df: %s" % (str(df.shape)))

    print("Removing combined duplicates")
    df = df.drop_duplicates(["allele", "peptide", "measurement_value"])
    print("New combined df: %s" % (str(df.shape)))

    df = df[[
        "allele",
        "peptide",
        "measurement_value",
        "measurement_inequality",
        "measurement_type",
        "measurement_source",
        "original_allele",
    ]].sort_values(["allele", "peptide"]).dropna()

    print("Final combined df: %s" % (str(df.shape)))

    df.to_csv(args.out_csv, index=False)
    print("Wrote: %s" % args.out_csv)

if __name__ == '__main__':
    run()
