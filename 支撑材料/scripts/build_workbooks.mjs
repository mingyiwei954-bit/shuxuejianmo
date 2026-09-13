import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const finalRoot = path.join(projectRoot, "outputs", "c_final_v1");
const frozenRoot = path.join(finalRoot, "frozen");
const workbookRoot = path.join(finalRoot, "workbooks");
const qaRoot = path.join(finalRoot, "qa", "workbook_renders");

function parseCsv(text) {
  const rows = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { value += '"'; i++; }
      else if (ch === '"') quoted = false;
      else value += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(value); value = ""; }
    else if (ch === '\n') { row.push(value.replace(/\r$/, "")); rows.push(row); row = []; value = ""; }
    else value += ch;
  }
  if (value.length || row.length) { row.push(value.replace(/\r$/, "")); rows.push(row); }
  if (rows.length && rows[0][0]?.charCodeAt(0) === 0xfeff) rows[0][0] = rows[0][0].slice(1);
  const headers = rows.shift();
  return rows.filter(r => r.some(v => v !== "")).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])));
}

async function readCsv(name) {
  return parseCsv(await fs.readFile(path.join(frozenRoot, name), "utf8"));
}

function n(v) {
  const x = Number(v);
  if (!Number.isFinite(x)) throw new Error(`Expected numeric value, got ${JSON.stringify(v)}`);
  return x;
}

function roundHalfUp(v, places = 4) {
  // Excel-facing values must follow the audit contract's decimal ROUND_HALF_UP
  // rule. Number.toFixed() rounds the already-binary IEEE-754 value and gives
  // the wrong result at exact decimal half units such as 2238.56265.
  const source = typeof v === "string" ? v.trim() : String(n(v));
  const match = source.match(/^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/);
  if (!match) throw new Error(`Expected decimal value, got ${JSON.stringify(v)}`);
  const negative = match[1] === "-";
  const fraction = match[3] ?? "";
  const exponent = Number(match[4] ?? 0);
  let magnitude = BigInt(`${match[2]}${fraction}` || "0");
  const scale = fraction.length - exponent;
  if (scale <= places) {
    magnitude *= 10n ** BigInt(places - scale);
  } else {
    const divisor = 10n ** BigInt(scale - places);
    const remainder = magnitude % divisor;
    magnitude /= divisor;
    if (remainder * 2n >= divisor) magnitude += 1n;
  }
  const signed = negative ? -magnitude : magnitude;
  return Number(signed) / 10 ** places;
}

function rounded4(v) { return roundHalfUp(v, 4); }

function decimalParts(v) {
  const source = typeof v === "string" ? v.trim() : String(n(v));
  const match = source.match(/^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/);
  if (!match) throw new Error(`Expected decimal value, got ${JSON.stringify(v)}`);
  const fraction = match[3] ?? "";
  const exponent = Number(match[4] ?? 0);
  let magnitude = BigInt(`${match[2]}${fraction}` || "0");
  let scale = fraction.length - exponent;
  if (scale < 0) {
    magnitude *= 10n ** BigInt(-scale);
    scale = 0;
  }
  if (match[1] === "-") magnitude = -magnitude;
  return { magnitude, scale };
}

function decimalSum(values) {
  const parts = values.map(decimalParts);
  const scale = Math.max(0, ...parts.map(p => p.scale));
  const total = parts.reduce(
    (acc, p) => acc + p.magnitude * 10n ** BigInt(scale - p.scale),
    0n,
  );
  const negative = total < 0n;
  const digits = (negative ? -total : total).toString().padStart(scale + 1, "0");
  if (scale === 0) return `${negative ? "-" : ""}${digits}`;
  return `${negative ? "-" : ""}${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
}
function excelDate(s) { return new Date(`${s}T00:00:00Z`); }

function officialLabel(position) {
  const start = position * 10;
  const end = (position + 1) * 10;
  const fmt = (mins) => {
    if (mins >= 1440) return `${Math.floor((mins - 1440) / 60)}:${String((mins - 1440) % 60).padStart(2, "0")}+1`;
    return `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
  };
  return `${fmt(start)}-${fmt(end)}`;
}

function physicalLabel(startPosition, endPositionExclusive) {
  const fmt = (mins) => `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
  return `${fmt((startPosition - 1) * 10)}-${fmt(endPositionExclusive * 10)}`;
}

function groupByDate(rows) {
  const out = new Map();
  for (const row of rows) {
    if (!out.has(row.date)) out.set(row.date, []);
    out.get(row.date).push(row);
  }
  for (const rs of out.values()) rs.sort((a, b) => n(a.position) - n(b.position));
  return out;
}

function validateDispatch(rows, name, expectedDays) {
  if (rows.length !== expectedDays * 144) throw new Error(`${name}: expected ${expectedDays * 144} rows, got ${rows.length}`);
  const byDate = groupByDate(rows);
  if (byDate.size !== expectedDays) throw new Error(`${name}: expected ${expectedDays} dates, got ${byDate.size}`);
  const referenceLabels = [...byDate.values()][0].map(r => r.official_label);
  if (referenceLabels.some(v => !v) || new Set(referenceLabels).size !== 144) {
    throw new Error(`${name}: official labels must contain 144 nonblank unique values`);
  }
  for (const [date, rs] of byDate) {
    if (rs.length !== 144) throw new Error(`${name} ${date}: expected 144 rows, got ${rs.length}`);
    for (let i = 0; i < 144; i++) {
      if (n(rs[i].position) !== i + 1) throw new Error(`${name} ${date}: bad position at ${i + 1}`);
      if (rs[i].official_label !== referenceLabels[i]) throw new Error(`${name} ${date}: official label mismatch at ${i + 1}`);
    }
  }
  return byDate;
}

function styleSheet(sheet, usedRange, numericRanges = []) {
  // Keep the template's cell boundaries visible. Several adjacent fields
  // (date/time and charge/discharge/time) otherwise read as one value in the
  // rendered workbook even though the underlying cells are correct.
  sheet.showGridLines = true;
  usedRange.format.font = { name: "Arial", size: 10, color: "#111827" };
  usedRange.format.verticalAlignment = "center";
  const header = usedRange.getRow(0);
  header.format.fill = "#1F4E78";
  header.format.font = { name: "Arial", size: 10, bold: true, color: "#FFFFFF" };
  header.format.horizontalAlignment = "center";
  header.format.wrapText = true;
  header.format.rowHeight = 30;
  for (const range of numericRanges) range.format.numberFormat = "0.0000";
}

function addPlanSheet(wb, name, byDate, valueField, costField) {
  const sheet = wb.worksheets.add(name);
  const labels = [...byDate.values()][0].map(r => r.official_label);
  const matrix = [["日期\\时间", ...labels, "全天购电量", "全天购电费"]];
  for (const [date, rows] of byDate) {
    matrix.push([
      excelDate(date),
      ...rows.map(r => rounded4(r[valueField])),
      rounded4(decimalSum(rows.map(r => r[valueField]))),
      rounded4(rows.reduce((s, r) => s + n(r[costField]), 0)),
    ]);
  }
  const used = sheet.getRangeByIndexes(0, 0, matrix.length, matrix[0].length);
  used.values = matrix;
  styleSheet(sheet, used, [sheet.getRangeByIndexes(1, 1, matrix.length - 1, matrix[0].length - 1)]);
  sheet.getRangeByIndexes(1, 0, matrix.length - 1, 1).format.numberFormat = "yyyy-mm-dd";
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  sheet.getRange(`A1:A${matrix.length}`).format.columnWidth = 12;
  sheet.getRange(`B1:EO${matrix.length}`).format.columnWidth = 10;
  sheet.getRange(`EP1:EQ${matrix.length}`).format.columnWidth = 15;
  return sheet;
}

function addQ1Sheets(wb, rows) {
  const plan = wb.worksheets.add("计划购电量");
  // result1's official template uses a different final label spelling from
  // the annual templates; preserve that literal template label.
  const planMatrix = [["时间段", "购电量"], ...rows.map((r, i) => [
    officialLabel(i + 1),
    rounded4(r.plan_00_grid_kwh),
  ])];
  const pUsed = plan.getRangeByIndexes(0, 0, planMatrix.length, 2);
  pUsed.values = planMatrix;
  styleSheet(plan, pUsed, [plan.getRange(`B2:B${planMatrix.length}`)]);
  plan.freezePanes.freezeRows(1);
  plan.getRange(`A1:A${planMatrix.length}`).format.columnWidth = 19;
  plan.getRange(`B1:B${planMatrix.length}`).format.columnWidth = 14;

  const charge = wb.worksheets.add("充放电量");
  const cm = [["时间段", "充电量", "放电量", "时刻", "储电量"]];
  for (let block = 0; block < 6; block++) {
    const rs = rows.slice(block * 24, (block + 1) * 24);
    cm.push([
      `${block * 4}:00-${(block + 1) * 4}:00`,
      rounded4(decimalSum(rs.map(r => r.charge_kwh))),
      rounded4(decimalSum(rs.map(r => r.discharge_kwh))),
      block === 0 ? "0:00" : block === 1 ? "24:00" : null,
      block === 0 ? rounded4(rows[0].soc_start_kwh) : block === 1 ? rounded4(rows[143].soc_end_kwh) : null,
    ]);
  }
  const cUsed = charge.getRangeByIndexes(0, 0, cm.length, 5);
  cUsed.values = cm;
  styleSheet(charge, cUsed, [charge.getRange("B2:C7"), charge.getRange("E2:E3")]);
  charge.getRange(`A1:E${cm.length}`).format.columnWidth = 18;
}

function addChargeSheet(wb, byDate) {
  const sheet = wb.worksheets.add("充放电量");
  const matrix = [["日期", "时间段", "充电量", "放电量", "时刻", "储电量"]];
  for (const [date, rows] of byDate) {
    for (let block = 0; block < 6; block++) {
      const rs = rows.slice(block * 24, (block + 1) * 24);
      matrix.push([
        block === 0 ? excelDate(date) : null,
        `${block * 4}:00-${(block + 1) * 4}:00`,
        rounded4(decimalSum(rs.map(r => r.charge_kwh))),
        rounded4(decimalSum(rs.map(r => r.discharge_kwh))),
        block === 0 ? "0:00" : block === 1 ? "24:00" : null,
        block === 0 ? rounded4(rows[0].soc_start_kwh) : block === 1 ? rounded4(rows[143].soc_end_kwh) : null,
      ]);
    }
  }
  const used = sheet.getRangeByIndexes(0, 0, matrix.length, 6);
  used.values = matrix;
  styleSheet(sheet, used, [sheet.getRangeByIndexes(1, 2, matrix.length - 1, 2), sheet.getRangeByIndexes(1, 5, matrix.length - 1, 1)]);
  sheet.getRangeByIndexes(1, 0, matrix.length - 1, 1).format.numberFormat = "yyyy-mm-dd";
  sheet.freezePanes.freezeRows(1);
  sheet.getRange(`A1:A${matrix.length}`).format.columnWidth = 13;
  sheet.getRange(`B1:B${matrix.length}`).format.columnWidth = 16;
  sheet.getRange(`C1:F${matrix.length}`).format.columnWidth = 14;
}

function addEmergencySheet(wb, byDate, threshold) {
  const sheet = wb.worksheets.add("紧急购电量");
  const matrix = [["日期", "购电时间段", "购电量"]];
  for (const [date, rows] of byDate) {
    const groups = [];
    let current = null;
    for (const r of rows) {
      const pos = n(r.position), q = n(r.emergency_kwh);
      // The configured half-unit threshold implements ROUND_HALF_UP at four decimals.
      const shown = Math.abs(q) >= threshold;
      if (!shown) { if (current) { groups.push(current); current = null; } continue; }
      if (!current) current = { start: pos, end: pos, amounts: [r.emergency_kwh] };
      else if (pos === current.end + 1) { current.end = pos; current.amounts.push(r.emergency_kwh); }
      else { groups.push(current); current = { start: pos, end: pos, amounts: [r.emergency_kwh] }; }
    }
    if (current) groups.push(current);
    groups.forEach((g, i) => matrix.push([i === 0 ? excelDate(date) : null, physicalLabel(g.start, g.end), rounded4(decimalSum(g.amounts))]));
  }
  const used = sheet.getRangeByIndexes(0, 0, matrix.length, 3);
  used.values = matrix;
  styleSheet(sheet, used, matrix.length > 1 ? [sheet.getRangeByIndexes(1, 2, matrix.length - 1, 1)] : []);
  if (matrix.length > 1) sheet.getRangeByIndexes(1, 0, matrix.length - 1, 1).format.numberFormat = "yyyy-mm-dd";
  sheet.freezePanes.freezeRows(1);
  sheet.getRange(`A1:A${matrix.length}`).format.columnWidth = 13;
  sheet.getRange(`B1:B${matrix.length}`).format.columnWidth = 18;
  sheet.getRange(`C1:C${matrix.length}`).format.columnWidth = 14;
}

function addEvidenceSheets(wb, byDate, mode) {
  const wanted = new Set(["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]);
  const matrix = [["日期", "物理时间段", "0点计划量", "最终购电量"]];
  for (const [day, rows] of byDate) {
    if (mode !== "q1" && !wanted.has(day)) continue;
    for (const hour of [10, 12, 14, 16, 18, 20]) {
      const row = rows.find(r => n(r.position) === hour * 6 + 1);
      matrix.push([excelDate(day), row.physical_interval, rounded4(row.plan_00_grid_kwh), rounded4(row.final_adjusted_grid_kwh)]);
    }
  }
  const sheet = wb.worksheets.add("指定时段");
  const used = sheet.getRangeByIndexes(0,0,matrix.length,4); used.values=matrix;
  styleSheet(sheet, used, [sheet.getRangeByIndexes(1,2,matrix.length-1,2)]);
  sheet.getRange(`A2:A${matrix.length}`).format.numberFormat="yyyy-mm-dd";
  sheet.getRange(`A1:D${matrix.length}`).format.columnWidth=19;
  const mapping=wb.worksheets.add("时段映射");
  const data=[["位置", "源时间戳", "物理区间", "原模板标签"], ...[...byDate.values()][0].map(r=>[n(r.position),r.source_timestamp,r.physical_interval,r.official_label])];
  const range=mapping.getRangeByIndexes(0,0,data.length,4);range.values=data;styleSheet(mapping,range);
  mapping.getRange("A1:D145").format.columnWidth=21;
}

async function exportAndVerify(wb, filename, sheetNames) {
  wb.recalculate();
  const file = path.join(workbookRoot, filename);
  const blob = await SpreadsheetFile.exportXlsx(wb);
  await blob.save(file);
  const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(file));
  const errors = await reopened.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 100 },
    maxChars: 6000,
    summary: `${filename} formula error scan`,
  });
  const errorLines = (errors.ndjson || "").split("\n").filter(line => /"address"\s*:/.test(line));
  if (errorLines.length) throw new Error(`${filename}: formula error detected: ${errorLines.join("\n")}`);
  // Some artifact-tool versions spill inspect output beside large workbooks.
  // It is a transient diagnostic, not part of the official submission.
  await fs.rm(`${file}.inspect.ndjson`, { force: true });
  const renderDir = path.join(qaRoot, filename.replace(/\.xlsx$/, ""));
  await fs.mkdir(renderDir, { recursive: true });
  for (const sheetName of sheetNames) {
    const sheet = reopened.worksheets.getItem(sheetName);
    const used = sheet.getUsedRange(true);
    const rowCount = used?.rowCount ?? 1;
    const colCount = used?.columnCount ?? 1;
    const ranges = [];
    if (colCount > 20) {
      ranges.push(`A1:P${Math.min(rowCount, 12)}`);
      ranges.push(`EI1:EQ${Math.min(rowCount, 12)}`);
      if (rowCount > 20) ranges.push(`A${Math.max(1, rowCount - 5)}:P${rowCount}`);
    } else {
      ranges.push(`A1:${String.fromCharCode(64 + Math.min(colCount, 26))}${Math.min(rowCount, 40)}`);
      if (rowCount > 45) ranges.push(`A${rowCount - 5}:${String.fromCharCode(64 + Math.min(colCount, 26))}${rowCount}`);
    }
    for (let i = 0; i < ranges.length; i++) {
      const png = await reopened.render({ sheetName, range: ranges[i], scale: 1.5, format: "png" });
      const safe = sheetName.replace(/[^\p{L}\p{N}_-]/gu, "_");
      await fs.writeFile(path.join(renderDir, `${safe}_${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
    }
  }
  return file;
}

async function main() {
  await fs.mkdir(workbookRoot, { recursive: true });
  await fs.mkdir(qaRoot, { recursive: true });
  const cfg = JSON.parse(await fs.readFile(path.join(projectRoot, "config", "final.yaml"), "utf8"));
  const threshold = Number(cfg.audit.emergency_display_omit_threshold_kwh);

  const specs = [
    ["q1_dispatch.csv", "result1.xlsx", "q1"],
    ["q2_dispatch.csv", "result2.xlsx", "q2"],
    ["q3_dispatch.csv", "result3.xlsx", "q3"],
    ["q4_2_dispatch.csv", "result4-2.xlsx", "q4_2"],
    ["q4_3_dispatch.csv", "result4-3.xlsx", "q4_3"],
  ];
  const created = [];
  for (const [csvName, xlsxName, mode] of specs) {
    const rows = await readCsv(csvName);
    const expectedDays = mode === "q1" ? 1 : 334;
    const byDate = validateDispatch(rows, mode, expectedDays);
    const wb = Workbook.create();
    let sheetNames;
    if (mode === "q1") {
      addQ1Sheets(wb, rows);
      sheetNames = ["计划购电量", "充放电量"];
    }
    else {
      const initialCostField = (mode === "q2" || mode === "q4_2") ? "final_relative_cost_yuan" : "plan_cost_yuan";
      addPlanSheet(wb, "计划购电量", byDate, "plan_00_grid_kwh", initialCostField);
      if (mode === "q3" || mode === "q4_3") addPlanSheet(wb, "调整购电量", byDate, "final_adjusted_grid_kwh", "final_relative_cost_yuan");
      addChargeSheet(wb, byDate);
      addEmergencySheet(wb, byDate, threshold);
      sheetNames = (mode === "q3" || mode === "q4_3")
        ? ["计划购电量", "调整购电量", "充放电量", "紧急购电量"]
        : ["计划购电量", "充放电量", "紧急购电量"];
    }
    addEvidenceSheets(wb, byDate, mode);
    sheetNames.push("指定时段", "时段映射");
    created.push(await exportAndVerify(wb, xlsxName, sheetNames));
  }
  await fs.writeFile(
    path.join(finalRoot, "qa", "workbook_build.json"),
    JSON.stringify({ created: created.map(file => path.relative(finalRoot, file)), threshold, verified: true }, null, 2),
  );
}

await main();
