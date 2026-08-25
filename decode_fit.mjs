
import { Decoder, Stream } from "@garmin/fitsdk";
import { readFileSync, readdirSync } from "node:fs";
const dir = process.argv[2];
const out = { sleepEvents: [], sleepLevels: [], hrData: [], monitoring: [], stress: [],
              respiration: [], hrvSummary: [], sleepAssessment: [] };
const iso = (t) => (t instanceof Date ? t.toISOString() : String(t));
for (const f of readdirSync(dir).filter((x) => x.endsWith(".fit"))) {
  try {
    const d = new Decoder(Stream.fromByteArray(new Uint8Array(readFileSync(dir + "/" + f))));
    const { messages } = d.read();
    const estSommeil = f.includes("SLEEP");
    // Les événements de session n'ont de sens que dans le fichier de sommeil :
    // les fichiers WELLNESS en contiennent d'autres, sans rapport.
    if (estSommeil)
      for (const e of messages.eventMesgs || [])
        out.sleepEvents.push({ t: iso(e.timestamp), type: e.eventType });
    for (const x of messages.sleepLevelMesgs || [])
      out.sleepLevels.push({ t: iso(x.timestamp), level: x.sleepLevel });
    for (const x of messages.sleepAssessmentMesgs || []) out.sleepAssessment.push(x);
    for (const x of messages.monitoringHrDataMesgs || [])
      out.hrData.push({ t: iso(x.timestamp), repos: x.restingHeartRate,
                        jour: x.currentDayRestingHeartRate });
    for (const x of messages.monitoringMesgs || [])
      out.monitoring.push({ t: iso(x.timestamp), steps: x.steps, activityType: x.activityType });
    for (const x of messages.stressLevelMesgs || []) out.stress.push(x.stressLevelValue);
    for (const x of messages.respirationRateMesgs || []) out.respiration.push(x.respirationRate);
    for (const x of messages.hrvStatusSummaryMesgs || []) out.hrvSummary.push(x);
  } catch (e) { /* fichier illisible : ignoré */ }
}
process.stdout.write(JSON.stringify(out));
