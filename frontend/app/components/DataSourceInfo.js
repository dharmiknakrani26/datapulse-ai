"use client";

import styles from "./DataSourceInfo.module.css";

export default function DataSourceInfo() {
  return (
    <div className={styles.wrapper}>
      <div className={styles.icon}>
        DH
      </div>

      <div className={styles.content}>
        <div className={styles.titleRow}>
          <strong>
            Data Source
          </strong>

          <span>
            DataHub Catalog
          </span>
        </div>

        <p>
          DataPulse investigates datasets already registered in
          DataHub. Search for an asset below, then launch an
          autonomous incident investigation across its metadata
          and lineage graph.
        </p>
      </div>

      <a
        href="http://localhost:9002"
        target="_blank"
        rel="noreferrer"
      >
        Browse Catalog ↗
      </a>
    </div>
  );
}