import { describe, it, expect } from "vitest";
import { Decoder, Stream } from "@garmin/fitsdk";
import { generateFit } from "../../src/viewer/lib/export/fit.js";
import type { Workout } from "../../src/schema/training-plan.js";
import type { Settings } from "../../src/viewer/stores/settings.js";

/**
 * FIT export regression tests.
 *
 * The other export formats (.ics, .zwo, .mrc) each had a test file; .fit did not,
 * which is how seven encoding bugs survived in it. Every case below fails against
 * the unfixed encoder, and each one produced a silent failure in practice: either
 * the SDK refused the file outright, or it accepted it and dropped the field —
 * leaving a watch showing an unnamed, structureless workout.
 *
 * These decode what was encoded rather than asserting on internals, so they stay
 * meaningful if the implementation changes.
 */

const settings = { units: "metric" } as unknown as Settings;

function decode(bytes: Uint8Array) {
  const decoder = new Decoder(Stream.fromByteArray(Array.from(bytes)));
  expect(decoder.isFIT()).toBe(true);
  expect(decoder.checkIntegrity()).toBe(true);
  const { messages, errors } = decoder.read();
  expect(errors).toHaveLength(0);
  return messages;
}

function runWorkout(overrides: Partial<Workout> = {}): Workout {
  return {
    id: "w1-tue-run",
    sport: "run",
    type: "endurance",
    name: "Easy Run",
    description: "Zone 2",
    durationMinutes: 45,
    ...overrides,
  } as Workout;
}

describe("FIT export", () => {
  it("produces a file the Garmin SDK can decode", async () => {
    const messages = decode(await generateFit(runWorkout(), settings));
    expect(messages.workoutMesgs).toBeDefined();
    expect(messages.workoutMesgs).toHaveLength(1);
  });

  it("carries the workout name — the watch shows this, never the filename", async () => {
    // Regression: the field was written as `workoutName`, which the SDK ignores in
    // silence. Every exported session arrived on the watch unnamed, and two sessions
    // with the same name collapsed into one entry in the workout list.
    const messages = decode(await generateFit(runWorkout({ name: "Threshold 3x10" }), settings));
    expect(messages.workoutMesgs[0].wktName).toBe("Threshold 3x10");
  });

  it("names each step", async () => {
    // Regression: written as `workoutStepName`, also silently ignored.
    const messages = decode(await generateFit(runWorkout(), settings));
    const named = messages.workoutStepMesgs.filter((s: any) => s.wktStepName);
    expect(named.length).toBeGreaterThan(0);
  });

  it("encodes heart-rate targets as bpm, not as a percentage of max", async () => {
    // Regression: FIT reads 1-100 as "% of max HR" and >100 as "bpm + 100".
    // Raw bpm were written, so a 145 bpm target was read back as 145 % of max.
    const workout = runWorkout({
      structure: {
        warmup: [],
        main: [
          {
            name: "Steady",
            type: "steady",
            duration: { unit: "seconds", value: 1800 },
            intensity: { unit: "hr_zone", value: 2, valueLow: 137, valueHigh: 150 },
          },
        ],
        cooldown: [],
      },
    } as Partial<Workout>);

    const messages = decode(await generateFit(workout, settings));
    const hrStep = messages.workoutStepMesgs.find(
      (s: any) => s.customTargetValueLow !== undefined && s.customTargetValueLow > 100,
    );
    expect(hrStep).toBeDefined();
    // 137 bpm encodes as 237, 150 bpm as 250
    expect(hrStep.customTargetValueLow).toBe(237);
    expect(hrStep.customTargetValueHigh).toBe(250);
  });

  it("places a repeat step after its children and points it at the first one", async () => {
    // Regression: the repeat step was inserted BEFORE its children with the repeat
    // count in `durationValue`. The FIT profile expects the opposite — the step comes
    // after the block, `durationValue` is the index of the first child, and
    // `targetValue` is how many times to repeat. Watches read the old form as garbage.
    const workout = runWorkout({
      structure: {
        warmup: [],
        main: [
          {
            name: "Intervals",
            repeats: 5,
            steps: [
              { name: "Hard", type: "interval", duration: { unit: "seconds", value: 180 },
                intensity: { unit: "hr_zone", value: 4 } },
              { name: "Float", type: "recovery", duration: { unit: "seconds", value: 90 },
                intensity: { unit: "hr_zone", value: 1 } },
            ],
          },
        ],
        cooldown: [],
      },
    } as Partial<Workout>);

    const messages = decode(await generateFit(workout, settings));
    const repeat = messages.workoutStepMesgs.find(
      (s: any) => s.durationType === "repeatUntilStepsCmplt",
    );
    expect(repeat).toBeDefined();
    expect(repeat.targetValue).toBe(5);
    // The repeat must sit after the two steps it loops over, and point back at the first
    expect(repeat.messageIndex).toBeGreaterThan(repeat.durationValue);
  });

  it("encodes strength sessions with a sub-sport the SDK accepts", async () => {
    // Regression: `strength_training` — snake_case — threw during encoding.
    const messages = decode(
      await generateFit(runWorkout({ sport: "strength", name: "Core" }), settings),
    );
    expect(messages.workoutMesgs[0].subSport).toBe("strengthTraining");
  });

  it("encodes swim sessions with a sub-sport the SDK accepts", async () => {
    // Regression: `lap_swimming` — same cause.
    const messages = decode(
      await generateFit(runWorkout({ sport: "swim", name: "Technique" }), settings),
    );
    expect(messages.workoutMesgs[0].subSport).toBe("lapSwimming");
  });
});
