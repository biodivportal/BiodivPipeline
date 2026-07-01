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
include { RDF_TRANSFORM        } from '../modules/local/rdf_transform/main'
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
    // directly. WP6's standardised CSV feeds the outlier + RDF branches.
    BIODIV_ANNOTATE( ch_input )
    ch_versions = ch_versions.mix(BIODIV_ANNOTATE.out.versions)

    // Only for demo purposes we gie some of the annotation output to the
    // taxonomy classifier

    def ch_enriched = BIODIV_ANNOTATE.out.enriched

    TAXONOMY_CLASSIFY( ch_enriched )
    ch_versions = ch_versions.mix(TAXONOMY_CLASSIFY.out.versions)

    OUTLIER_DETECT( ch_standardised )
    ch_versions = ch_versions.mix(OUTLIER_DETECT.out.versions)

    // WP5 can be skipped (runs on the host, needs extra deps + an LLM key). When
    // skipped, feed COLLECT_REPORTS an empty placeholder instead of its output.
    def ch_concepts
    if (params.skip_provisional_concepts) {
        ch_concepts = channel.fromPath("${projectDir}/assets/NO_FILE")
    } else {
        PROVISIONAL_CONCEPTS( BIODIV_ANNOTATE.out.unresolved )
        ch_versions = ch_versions.mix(PROVISIONAL_CONCEPTS.out.versions)
        ch_concepts = PROVISIONAL_CONCEPTS.out.concepts
    }

    RDF_TRANSFORM(
        ch_standardised,
        BIODIV_ANNOTATE.out.annotations,
        TAXONOMY_CLASSIFY.out.resolved,
        ch_schema
    )
    ch_versions = ch_versions.mix(RDF_TRANSFORM.out.versions)

    COLLECT_REPORTS(
        OUTLIER_DETECT.out.flagged,
        RDF_TRANSFORM.out.report,
        COLUMN_STANDARDISE.out.mapping,
        ch_concepts
    )

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
    rdf_turtle   = RDF_TRANSFORM.out.rdf_turtle       // channel: path to Turtle RDF output
    rdf_jsonld   = RDF_TRANSFORM.out.rdf_jsonld        // channel: path to JSON-LD RDF output
    flagged      = OUTLIER_DETECT.out.flagged           // channel: path to flagged records
    taxonomy     = TAXONOMY_CLASSIFY.out.resolved       // channel: path to resolved taxonomy
    summary      = COLLECT_REPORTS.out.summary           // channel: path to pipeline summary
    versions     = ch_versions                           // channel: [ path(versions.yml) ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
