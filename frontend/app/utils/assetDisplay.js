const ACRONYMS = {
  ai: "AI",
  api: "API",
  bi: "BI",
  dbt: "dbt",
  elt: "ELT",
  etl: "ETL",
  id: "ID",
  kpi: "KPI",
  s3: "S3",
  sql: "SQL",
};


export function formatAssetName(value) {
  if (!value) {
    return "Unknown Asset";
  }

  return String(value)
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .map((word) => {
      if (!word) {
        return word;
      }

      const lowerWord =
        word.toLowerCase();

      if (ACRONYMS[lowerWord]) {
        return ACRONYMS[lowerWord];
      }

      return (
        word.charAt(0).toUpperCase() +
        word.slice(1)
      );
    })
    .join(" ");
}


export function extractAssetName(value) {
  if (!value) {
    return "Unknown Asset";
  }

  let name =
    String(value).trim();


  /*
    DATASET URN

    Example:
    urn:li:dataset:(
      urn:li:dataPlatform:dbt,
      b2fd91.order_entry_db.order_entry.orders,
      PROD
    )
  */

  const datasetMatch =
    name.match(
      /urn:li:dataset:\(urn:li:dataPlatform:[^,]+,([^,]+),[^\)]+\)/i
    );

  if (
    datasetMatch &&
    datasetMatch[1]
  ) {
    name =
      datasetMatch[1];
  }


  /*
    DATA JOB URN

    Extract the final data job name.
  */

  if (
    name.includes(
      "urn:li:dataJob:"
    )
  ) {
    const lastComma =
      name.lastIndexOf(",");

    if (
      lastComma !== -1
    ) {
      name =
        name
          .slice(
            lastComma + 1
          )
          .replace(
            /\)+$/,
            ""
          )
          .trim();
    }
  }


  /*
    DATA FLOW URN
  */

  const dataFlowMatch =
    name.match(
      /urn:li:dataFlow:\([^,]+,([^,]+),[^\)]+\)/i
    );

  if (
    dataFlowMatch &&
    dataFlowMatch[1]
  ) {
    name =
      dataFlowMatch[1];
  }


  name = name
    .replace(/[()]/g, "")
    .replace(/`/g, "")
    .trim();


  /*
    Database-style path:

    b2fd91.order_entry_db.order_entry.orders

    becomes:

    orders
  */

  if (
    name.includes(".")
  ) {
    const segments =
      name
        .split(".")
        .filter(Boolean);

    name =
      segments[
        segments.length - 1
      ] || name;
  }


  return formatAssetName(
    name
  );
}


export function getAssetDisplayName(
  name,
  urn
) {
  if (
    name &&
    name !==
      "Unknown Dataset" &&
    name !==
      "Unknown Asset"
  ) {
    if (
      String(name).includes(
        "urn:li:"
      )
    ) {
      return extractAssetName(
        name
      );
    }

    return formatAssetName(
      name
    );
  }

  return extractAssetName(
    urn
  );
}


/*
  Clean technical identifiers from
  AI-generated text for frontend display.

  The backend data stays unchanged.
*/

export function cleanTechnicalText(
  value
) {
  if (!value) {
    return "";
  }

  let text =
    String(value);


  /*
    Replace Dataset URNs
  */

  text = text.replace(
    /`?urn:li:dataset:\(urn:li:dataPlatform:[^,]+,([^,]+),[^\)]+\)`?/gi,

    (
      match,
      assetName
    ) =>
      extractAssetName(
        assetName
      )
  );


  /*
    Replace Data Flow URNs
  */

  text = text.replace(
    /`?urn:li:dataFlow:\([^,]+,([^,]+),[^\)]+\)`?/gi,

    (
      match,
      assetName
    ) =>
      formatAssetName(
        assetName
      )
  );


  /*
    Clean anything wrapped in backticks.

    Example:

    `export_table_orders_to_s3`

    becomes:

    Export Table Orders To S3
  */

  text = text.replace(
    /`([^`]+)`/g,

    (
      match,
      identifier
    ) => {
      if (
        identifier.includes(
          "urn:li:"
        )
      ) {
        return extractAssetName(
          identifier
        );
      }


      if (
        /^[A-Za-z0-9_.-]+$/.test(
          identifier
        )
      ) {
        return extractAssetName(
          identifier
        );
      }


      return identifier;
    }
  );


  /*
    Clean remaining underscore-heavy
    technical identifiers.

    Example:

    import_table_orders_to_snowflake

    becomes:

    Import Table Orders To Snowflake
  */

  text = text.replace(
    /\b[A-Za-z0-9]+(?:_[A-Za-z0-9]+){2,}\b/g,

    (
      identifier
    ) =>
      formatAssetName(
        identifier
      )
  );


  return text
    .replace(
      /\s+/g,
      " "
    )
    .trim();
}


export function formatIncidentType(
  value
) {
  const labels = {
    freshness:
      "Freshness Failure",

    data_quality:
      "Data Quality Failure",

    schema_change:
      "Schema Change",
  };


  return (
    labels[value] ||
    formatAssetName(
      value
    )
  );
}