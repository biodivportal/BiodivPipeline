/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
include { COLUMN_STANDARDISE   } from '../modules/local/column_standardise/main'
include { BIODIV_ANNOTATE      } from '../modules/local/biodiv_annotate/main'
include { TAXONOMY_CLASSIFY    } from '../modules/local/taxonomy_classify/main'
include { OUTLIER_DETECT       } from '../modules/local/outlier_detect/main'
include { PROVISIONAL_CONCEPTS } from '../modules/local/provisional_concepts/main'
include { RDF_TRANSFORM        } from '../modules/local/rdf_transform/nextflow/main'
include { ASSEMBLE_DATASET     } from '../modules/local/assemble_dataset/main'
include { COLLECT_REPORTS      } from '../modules/local/collect_reports/main'
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow BIODIVPIPELINE {

    take:
    ch_input       // channel: path to input CSV file
    ch_schema      // channel: path to RDF mapping schema (JSON-LD or Turtle)
    outdir

    main:

    def ch_versions = channel.empty()

    COLUMN_STANDARDISE( ch_input )
    ch_versions = ch_versions.mix(COLUMN_STANDARDISE.out.versions)

    def ch_standardised = COLUMN_STANDARDISE.out.csv

    // WP2 (annotation) and WP3 (taxonomy) resolve against the ORIGINAL BGBM column
    // names (HerbariumID, FullNameCache, Genus, Family, ...). WP6 renames those columns
    // in its standardised output, so the annotation branch consumes the raw input
    // directly. WP6's standardised CSV feeds RDF branch.
    BIODIV_ANNOTATE( ch_input )
    ch_versions = ch_versions.mix(BIODIV_ANNOTATE.out.versions)

    // Only for demo purposes we gie some of the annotation output to the
    // taxonomy classifier

    def ch_enriched = BIODIV_ANNOTATE.out.enriched

    TAXONOMY_CLASSIFY( ch_enriched )
    ch_versions = ch_versions.mix(TAXONOMY_CLASSIFY.out.versions)

    OUTLIER_DETECT( ch_input )
    ch_versions = ch_versions.mix(OUTLIER_DETECT.out.versions)

    // WP5 can be skipped (its ENVO/locality path needs a WP5_OPENAI_API_KEY secret). When
    // skipped, feed COLLECT_REPORTS an empty placeholder instead of its output.
    def ch_concepts
    if (params.skip_provisional_concepts) {
        ch_concepts = channel.fromPath("${projectDir}/assets/NO_FILE")
    } else {
        PROVISIONAL_CONCEPTS( BIODIV_ANNOTATE.out.unresolved )
        ch_versions = ch_versions.mix(PROVISIONAL_CONCEPTS.out.versions)
        ch_concepts = PROVISIONAL_CONCEPTS.out.concepts
    }

    // Output (ii): RDF triples via the WP7/WP8 RDF Matching & Transformation service.
    // The service needs an RML mapping (from the WP8 Schema Editor) whose columns match
    // the dataset. Until a matching mapping exists for the BGBM data — and while its
    // image lives in a registry we cannot all pull — RDF is skippable so the rest of the
    // pipeline stays green. Enable with `--skip_rdf false --mapping_schema <real RML>`.
    def ch_rdf
    def ch_rdf_report
    if (params.skip_rdf) {
        ch_rdf        = channel.empty()
        ch_rdf_report = channel.fromPath("${projectDir}/assets/NO_FILE")
    } else {
        RDF_TRANSFORM( ch_standardised, ch_schema )
        ch_versions   = ch_versions.mix(RDF_TRANSFORM.out.versions)
        ch_rdf        = RDF_TRANSFORM.out.rdf
        ch_rdf_report = RDF_TRANSFORM.out.validate
    }

    // Output (i): assemble the single quality-annotated, taxonomically resolved
    // dataset by joining the annotated records with taxonomy resolution + quality
    // flags (Lastenheft Requirement 1).
    ASSEMBLE_DATASET(
        ch_enriched,
        TAXONOMY_CLASSIFY.out.resolved,
        OUTLIER_DETECT.out.flagged
    )
    ch_versions = ch_versions.mix(ASSEMBLE_DATASET.out.versions)

    // Output (iii): collect per-step quality reports into one summary.
    COLLECT_REPORTS(
        COLUMN_STANDARDISE.out.mapping,
        BIODIV_ANNOTATE.out.unresolved,
        TAXONOMY_CLASSIFY.out.resolved,
        OUTLIER_DETECT.out.flagged,
        ch_concepts,
        ch_rdf_report
    )
    ch_versions = ch_versions.mix(COLLECT_REPORTS.out.versions)

    //
    // Collate software versions
    //
    softwareVersionsToYAML(ch_versions)
        .collectFile(
            storeDir: "${outdir}/pipeline_info",
            name: 'biodivpipeline_software_versions.yml',
            sort: true,
            newLine: true
        )

    emit:
    final_dataset = ASSEMBLE_DATASET.out.dataset        // channel: path to unified quality-annotated + taxonomically resolved dataset
    rdf          = ch_rdf                                 // channel: path to RDF output (empty when --skip_rdf)
    flagged      = OUTLIER_DETECT.out.flagged           // channel: path to flagged records
    taxonomy     = TAXONOMY_CLASSIFY.out.resolved       // channel: path to resolved taxonomy
    report       = COLLECT_REPORTS.out.report            // channel: path to human-readable quality report
    summary      = COLLECT_REPORTS.out.summary           // channel: path to pipeline summary
    versions     = ch_versions                           // channel: [ path(versions.yml) ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
