import json
from datetime import datetime
import os

DEFAULT_VERSION = "1.0.0"
DEFAULT_LICENSE = "https://creativecommons.org/publicdomain/zero/1.0/"
DEFAULT_REPOSITORY = "https://github.com/bernardobap21/DMP-Evaluation"

# Mapping from FAIR principles to human readable benchmark titles
BENCHMARK_TITLES = {
    "F1": "Identifier type",
    "F2": "Metadata schema",
    "F3": "Metadata-Data linking mechanism",
    "F4": "Registry (searchable repository)",
    "A1.1": "Communication protocol",
    "A1.2": "Authentication and authorization service",
    "A2": "Metadata repository",
    "I1": "Knowledge representation language",
    "I2": "Structured vocabulary",
    "I3": "Qualified reference mechanism",
    "R1.1": "Data usage license",
    "R1.2": "Provenance model",
}

def export_planned_fairness(test_results, dmp_id, output_path):
    output = {
        "@context": "https://w3id.org/ostrails/fair-assessment/context",
        "@type": "AssessmentResult",
        "evaluated_resource": dmp_id,
        "date": datetime.now().isoformat(),
        "results": []
    }

    for test in test_results:
        output["results"].append({
            "@type": "TestResult",
            "test_id": test.get("test_id"),
            "test_name": test.get("test_name"),
            "test_description": test.get("test_description"),
            "test_status": test.get("status"),
            "comment": test.get("comment", "")
        })

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)


    print(f"Planned FAIRness (OSTrails format) saved to {output_path}")


def export_fip_results(results, dmp_id, dmp_title, output_dir, metric_version=DEFAULT_VERSION):
    
    graph = []

    dmp_entity_id = "#input_dmp"
    graph.append(
        {
            "@id": dmp_entity_id,
            "@type": "prov:Entity",
            "dcterms:identifier": dmp_id,
            "dcterms:title": dmp_title,
            "dcterms:description": "Input maDMP",
        }
    )

    org_id = "#evaluation_org"
    graph.append(
        {
            "@id": org_id,
            "@type": "vcard:Organization",
            "vcard:fn": "OSTrails",
            "vcard:organization-name": "OSTrails",
            "vcard:hasEmail": "mailto:info@ostrails.org",
        }
    )

    algorithm_id = "#evaluation_algorithm"
    algorithm_node = {
        "@id": algorithm_id,
        "@type": ["ftr:Algorithm", "dcat:DataService", "prov:Agent"],
        "dcterms:identifier": "ostrails-algorithm",
        "dcterms:title": "maDMP Evaluation Algorithm",
        "dcterms:description": "Algorithm that evaluates maDMP fields against a FIP",
        "dcterms:license": DEFAULT_LICENSE,
        "dcat:version": metric_version,
        "doap:repository": DEFAULT_REPOSITORY,
        "sio:is-implementation-of": [],
        "dcterms:creator": org_id,
    }
    graph.append(algorithm_node)

    exec_id = "#test_execution"
    execution_activity = {
        "@id": exec_id,
        "@type": "ftr:TestExecutionActivity",
        "prov:wasAssociatedWith": [],
        "prov:generated": [],
        "prov:used": dmp_entity_id,
    }


    result_set_id = f"#{dmp_id}_results"
    result_set = {
        "@id": result_set_id,
        "@type": ["ftr:TestResultSet", "prov:Entity", "prov:Collection"],
        "dcterms:identifier": dmp_id,
        "dcterms:title": f"Evaluation results for DMP: {dmp_title}",
        "dcterms:license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "prov:hadMember": [],
        "prov:wasDerivedFrom": dmp_entity_id,
        "prov:wasGeneratedBy": exec_id,
    }
    graph.append(result_set)

    ###
    benchmarks = {}
    ###

    for res in results:
        metric_uri = f"#{res['metric_id']}"
        metric = {
            "@id": metric_uri,
            "@type": "dqv:Metric",
            "dcterms:identifier": res["metric_id"],
            "dcterms:title": res["metric_label"],
            "dcterms:description": res["metric_label"],
            "dcat:version": metric_version,
        }
        graph.append(metric)

        #####
        principle = res.get("fair_principle")
        bench_uri = None
        if principle:
            bench_uri = f"#{principle}_benchmark"
            if principle not in benchmarks:
                benchmarks[principle] = {
                    "@id": bench_uri,
                    "@type": "ftr:Benchmark",
                    "dcterms:identifier": principle,
                    "dcterms:title": BENCHMARK_TITLES.get(principle, principle),
                    "dcterms:description": f"Metrics for FAIR principle {principle}",
                    "dcat:version": metric_version,
                    "ftr:hasAssociatedMetric": [],
                }
            if metric_uri not in benchmarks[principle]["ftr:hasAssociatedMetric"]:
                benchmarks[principle]["ftr:hasAssociatedMetric"].append(metric_uri)
        ####

        test_uri = f"#{res['test_id']}"
        allowed_vals = res.get("benchmark", [])
        if not isinstance(allowed_vals, list):
            allowed_vals = [allowed_vals] if allowed_vals else []

        description = (
            f"DCS field: {res['subject']}; allowed_value from the community: "
            f"{json.dumps(allowed_vals, ensure_ascii=False)}"
        )
        test_node = {
            "@id": test_uri,
            "@type": ["ftr:Test", "dcat:DataService", "prov:Agent"],
            "dcterms:identifier": res["test_id"],
            "dcterms:title": res["metric_label"],
            "dcterms:description": description,
            "dcterms:license": DEFAULT_LICENSE,
            "dcat:version": metric_version,
            "sio:is-implementation-of": metric_uri,
            "ftr:testMetric": metric_uri,
        }
        graph.append(test_node)

        """"
        for idx, val in enumerate(res.get("benchmark", []), start=1):
            bench_uri = f"#{res['test_id']}_benchmark_{idx}"
            bench = {
                "@id": bench_uri,
                "@type": "ftr:Benchmark",
                "dcterms:identifier": str(val),
                "dcterms:title": str(val),
                "dcterms:description": f"Allowed value: {val}",
                "dcat:version": metric_version,
                "ftr:hasAssociatedMetric": metric_uri,
            }
            graph.append(bench)
            test_node["ftr:hasBenchmark"].append(bench_uri)
        """
        ###
        if bench_uri and bench_uri not in algorithm_node["sio:is-implementation-of"]:
        ###
            algorithm_node["sio:is-implementation-of"].append(bench_uri)

        execution_activity["prov:wasAssociatedWith"].append(test_uri)

        result_uri = f"#{res['test_id']}_result"
        status = res["status"]
        log_value = res.get("log_value")
        result_node = {
            "@id": result_uri,
            "@type": ["ftr:TestResult", "prov:Entity"],
            "dcterms:identifier": res["test_id"],
            "dcterms:title": f"Result for {res['metric_id']}",
            "dcterms:description": res["comment"],
            "dcterms:license": "https://creativecommons.org/publicdomain/zero/1.0/",
            "prov:value": status,
            "ftr:log": log_value,
            "ftr:completion": "100",
            "ftr:outputFromTest": test_uri,
            "prov:wasDerivedFrom": dmp_entity_id,
        }
        graph.append(result_node)
        result_set["prov:hadMember"].append(result_uri)
        execution_activity["prov:generated"].append(result_uri)
    
    ###
    for bench in benchmarks.values():
        graph.append(bench)
    ###

    graph.append(execution_activity)

    out = {
        "@context": {
        "prov": "http://www.w3.org/ns/prov#",
        "ftr": "https://w3id.org/ftr#",
        "dcat": "http://www.w3.org/ns/dcat#",
        "sio": "http://semanticscience.org/resource/",
        "dcterms": "http://purl.org/dc/terms/",
        "doap": "http://usefulinc.com/ns/doap#",
        "adms": "http://www.w3.org/ns/adms#",
        "vivo": "http://vivoweb.org/ontology/core#",
        "dpv": "http://www.w3id.org/dpv#",  
        "vcard": "http://www.w3.org/2006/vcard/ns#",
        "dqv": "http://www.w3.org/ns/dqv#"  
    },
        "@graph": graph,
        
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{dmp_id}_ostrails_results.jsonld")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    return output_path
