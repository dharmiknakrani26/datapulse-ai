"use client";

import styles from "./IncidentEvidence.module.css";

import {
  cleanTechnicalText,
} from "../utils/assetDisplay";


export default function IncidentEvidence({
  evidence = [],
  limitations = [],
}) {
  if (
    evidence.length === 0 &&
    limitations.length === 0
  ) {
    return null;
  }


  return (
    <article
      className={`panel ${styles.panel}`}
    >
      <div className={styles.header}>
        <div>
          <p className="eyebrow">
            GROUNDED AI REASONING
          </p>

          <h3>
            Evidence & Limitations
          </h3>

          <p className={styles.description}>
            DataPulse separates
            DataHub-grounded evidence
            from assumptions that still
            require verification.
          </p>
        </div>


        <span className={styles.badge}>
          Trust Layer
        </span>
      </div>


      <div className={styles.grid}>
        {/* Confirmed Evidence */}

        <section
          className={
            styles.evidenceSection
          }
        >
          <div
            className={
              styles.sectionHeader
            }
          >
            <div
              className={
                styles.evidenceIcon
              }
            >
              ✓
            </div>

            <div>
              <strong>
                Confirmed Evidence
              </strong>

              <span>
                Grounded in DataHub
                metadata and lineage
              </span>
            </div>
          </div>


          {evidence.length >
          0 ? (
            <div
              className={
                styles.itemList
              }
            >
              {evidence.map(
                (
                  item,
                  index
                ) => (
                  <div
                    className={
                      styles.evidenceItem
                    }
                    key={`${index}-${item}`}
                  >
                    <span
                      className={
                        styles.itemNumber
                      }
                    >
                      {index + 1}
                    </span>

                    <p>
                      {cleanTechnicalText(
                        item
                      )}
                    </p>
                  </div>
                )
              )}
            </div>
          ) : (
            <p
              className={
                styles.empty
              }
            >
              No explicit evidence
              was returned.
            </p>
          )}
        </section>


        {/* Analysis Limitations */}

        <section
          className={
            styles.limitationsSection
          }
        >
          <div
            className={
              styles.sectionHeader
            }
          >
            <div
              className={
                styles.warningIcon
              }
            >
              !
            </div>

            <div>
              <strong>
                Analysis Limitations
              </strong>

              <span>
                Information that is not
                independently proven
              </span>
            </div>
          </div>


          {limitations.length >
          0 ? (
            <div
              className={
                styles.itemList
              }
            >
              {limitations.map(
                (
                  item,
                  index
                ) => (
                  <div
                    className={
                      styles.limitationItem
                    }
                    key={`${index}-${item}`}
                  >
                    <span
                      className={
                        styles.itemNumber
                      }
                    >
                      {index + 1}
                    </span>

                    <p>
                      {cleanTechnicalText(
                        item
                      )}
                    </p>
                  </div>
                )
              )}
            </div>
          ) : (
            <p
              className={
                styles.empty
              }
            >
              No additional
              limitations were
              reported.
            </p>
          )}
        </section>
      </div>
    </article>
  );
}