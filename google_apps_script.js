// ============================================================
//  FANMILK TOGO — Google Apps Script (API Dashboard)
//
//  📌 COMMENT L'UTILISER :
//  1. Ouvrez votre Google Sheet Togo
//  2. Extensions → Apps Script
//  3. Supprimez tout le code existant
//  4. Collez TOUT ce fichier
//  5. Ligne 12 : remplacez COLLEZ_VOTRE_SHEET_ID_ICI
//     par l'ID de votre Sheet (dans l'URL entre /d/ et /edit)
//  6. Déployer → Nouveau déploiement → Application Web
//     → Exécuter en tant que : Moi
//     → Accès : Tout le monde
//  7. Copiez l'URL → collez dans Vercel VITE_APPS_SCRIPT_URL
//
//  ✅ RÈGLE VENTES :
//  "Je vais vendre"  → chiffres = VENTES DE LA VEILLE
//  "Je ne vends pas" → chiffres = VENTES DE LA VEILLE
//  "J ai deja vendu" → chiffres = VENTES D'AUJOURD'HUI
//
//  ✅ CE QUE CE SCRIPT FAIT :
//  - Lit Reponses Vendors + Vendors
//  - Renvoie un JSON au dashboard React (Vercel)
//  - Applique la bonne logique ventes sans biais
//  - Calcule satisfaction, equipment, QPVD, dépôts, etc.
// ============================================================

var SHEET_ID       = "COLLEZ_VOTRE_SHEET_ID_ICI";
var SHEET_VENDORS  = "Vendors";
var SHEET_REPONSES = "Reponses Vendors";
var TIMEZONE       = "Africa/Lome";

var V_PHONE=0,V_NOM=1,V_DEPOT=2,V_LAST_DEC=3;
var V_VENTES=4,V_FANXTRA=5,V_FANCHOCO=6,V_FANVAN=7,V_PIECES=8,V_DATE_V=9;

var R_DATE=0,R_HEURE=1,R_PERIODE=2,R_PHONE=3,R_NOM=4,R_DEPOT=5;
var R_STATUT=6,R_VENTES=7,R_XTRA=8,R_CHOCO=9,R_VAN=10;
var R_LIEU=11,R_CAT=12,R_PRIME=13,R_COMM=14;

// Statuts = ventes d'AUJOURD'HUI
var STATUTS_AUJOURD_HUI = ["J ai deja vendu"];
// Statuts = ventes de la VEILLE
var STATUTS_HIER = ["Je vais vendre", "Non"];


function doGet(e) {
  try {
    var out = ContentService.createTextOutput(JSON.stringify(buildData()));
    out.setMimeType(ContentService.MimeType.JSON);
    return out;
  } catch(err) {
    var e2 = ContentService.createTextOutput(JSON.stringify({error:err.message}));
    e2.setMimeType(ContentService.MimeType.JSON);
    return e2;
  }
}


function buildData() {
  var ss         = SpreadsheetApp.openById(SHEET_ID);
  var vendorRows = readSheet(ss, SHEET_VENDORS);
  var repRows    = readSheet(ss, SHEET_REPONSES);
  var today      = Utilities.formatDate(new Date(), TIMEZONE, "dd/MM/yyyy");
  var yesterday  = getYesterday(today);

  return {
    updated_at         : new Date().toISOString(),
    today_date         : today,
    yesterday_date     : yesterday,
    vendors            : buildVendors(vendorRows, repRows),
    weekly             : buildWeekly(repRows),
    today              : buildToday(repRows, today),
    yesterday          : buildYesterday(repRows, today, yesterday),
    depots             : buildDepots(repRows),
    depot_today        : buildDepotByDay(repRows, today, "today"),
    depot_yesterday    : buildDepotByDay(repRows, today, "yesterday"),
    problems           : buildProblems(repRows, today),
    prime              : buildPrime(repRows),
    hotspots           : buildHotspots(repRows),
    morning_vs_evening : buildMorningEvening(repRows),
    satisfaction       : buildSatisfaction(repRows, today),
    equipment          : buildEquipment(repRows, today),
  };
}

function readSheet(ss, name) {
  var s = ss.getSheetByName(name);
  if (!s) return [];
  var v = s.getDataRange().getValues();
  return v.length>1 ? v.slice(1).filter(function(r){return String(r[0]||"").trim();}) : [];
}

// Calcule la date d'hier en dd/MM/yyyy
function getYesterday(todayStr) {
  var p = todayStr.split("/");
  var d = new Date(parseInt(p[2]), parseInt(p[1])-1, parseInt(p[0]));
  d.setDate(d.getDate()-1);
  var dd = d.getDate()<10?"0"+d.getDate():String(d.getDate());
  var mm = (d.getMonth()+1)<10?"0"+(d.getMonth()+1):String(d.getMonth()+1);
  return dd+"/"+mm+"/"+d.getFullYear();
}

// Est-ce que ce statut correspond aux ventes du jour ?
function isVenteAujourdHui(statut) {
  return STATUTS_AUJOURD_HUI.indexOf(statut) !== -1;
}

// Est-ce que ce statut correspond aux ventes de la veille ?
function isVenteHier(statut) {
  return STATUTS_HIER.indexOf(statut) !== -1;
}


// ============================================================
//  VENDORS — jours réels depuis Réponses
// ============================================================
function buildVendors(vendorRows, repRows) {
  var joursParPhone = {};
  repRows.forEach(function(r) {
    var ph   = String(r[R_PHONE]||"").trim();
    var date = String(r[R_DATE] ||"").trim();
    if (!ph || !date) return;
    if (!joursParPhone[ph]) joursParPhone[ph] = {};
    joursParPhone[ph][date] = true;
  });

  return vendorRows.map(function(r) {
    var phone    = String(r[V_PHONE]||"").trim();
    var fanxtra  = parseInt(r[V_FANXTRA]) ||0;
    var fanchoco = parseInt(r[V_FANCHOCO])||0;
    var fanvan   = parseInt(r[V_FANVAN])  ||0;
    var jours    = joursParPhone[phone]
      ? Object.keys(joursParPhone[phone]).length : 0;
    return {
      phone:phone, nom:String(r[V_NOM]||"").trim(),
      depot:String(r[V_DEPOT]||"").trim(),
      last_decl:String(r[V_LAST_DEC]||"").trim(),
      ventes:parseInt(r[V_VENTES])||0,
      fanxtra:fanxtra, fanchoco:fanchoco, fanvanille:fanvan,
      pieces:parseInt(r[V_PIECES])||(fanxtra+fanchoco+fanvan),
      jours:jours, prev_ventes:0,
      last_date:String(r[V_DATE_V]||"").trim(),
    };
  }).filter(function(v){return v.nom;});
}


// ============================================================
//  TODAY — uniquement "J'ai déjà vendu" du jour
// ============================================================
function buildToday(rows, today) {
  var todayRows = rows.filter(function(r){
    return String(r[R_DATE]||"").trim() === today;
  });

  // Un seul enregistrement par vendor (le dernier)
  var parPhone = {};
  todayRows.forEach(function(r){
    var ph=String(r[R_PHONE]||"").trim();
    if(ph) parPhone[ph]=r;
  });

  var vendorsUniques=Object.keys(parPhone).length;
  var ventes=0,xtra=0,choco=0,van=0,aucunPb=0,vendorsQuiVendent=0;

  Object.values(parPhone).forEach(function(r){
    var stat=String(r[R_STATUT]||"").trim();
    var cat =String(r[R_CAT]   ||"").trim();
    if(cat==="Aucun probleme"||cat==="") aucunPb++;
    // ✅ Ventes d'aujourd'hui = seulement "J ai deja vendu"
    if(isVenteAujourdHui(stat)){
      ventes+=parseInt(r[R_VENTES])||0;
      xtra  +=parseInt(r[R_XTRA])  ||0;
      choco +=parseInt(r[R_CHOCO]) ||0;
      van   +=parseInt(r[R_VAN])   ||0;
      vendorsQuiVendent++;
    }
  });

  var last10=todayRows.slice(-10).reverse().map(function(r){
    var stat=String(r[R_STATUT]||"").trim();
    return {
      heure :String(r[R_HEURE] ||""),
      nom   :String(r[R_NOM]   ||""),
      depot :String(r[R_DEPOT] ||""),
      statut:stat,
      ventes:parseInt(r[R_VENTES])||0,
      xtra  :parseInt(r[R_XTRA])  ||0,
      choco :parseInt(r[R_CHOCO]) ||0,
      van   :parseInt(r[R_VAN])   ||0,
      cat   :String(r[R_CAT]   ||""),
      periode_ventes: isVenteAujourdHui(stat) ? "today" : "yesterday",
    };
  });

  return {
    nb_declarations    : todayRows.length,
    vendors_uniques    : vendorsUniques,
    vendors_qui_vendent: vendorsQuiVendent,
    ventes_total       : ventes,
    fanxtra_total      : xtra,
    fanchoco_total     : choco,
    fanvan_total       : van,
    satisfaction_today : vendorsUniques>0?Math.round((aucunPb/vendorsUniques)*100):0,
    last_declarations  : last10,
  };
}


// ============================================================
//  YESTERDAY — ventes déclarées comme "veille"
//  = lignes d'HIER avec "Je vais vendre"/"Non"
//  + lignes d'AUJOURD'HUI avec "Je vais vendre"/"Non"
//  (les deux représentent les ventes de la veille)
// ============================================================
function buildYesterday(rows, today, yesterday) {
  var ventes=0,xtra=0,choco=0,van=0,count=0;

  rows.forEach(function(r){
    var date=String(r[R_DATE]||"").trim();
    var stat=String(r[R_STATUT]||"").trim();

    // Lignes d'aujourd'hui avec statut "veille"
    var estAujourdHuiVeille = (date===today && isVenteHier(stat));
    // Lignes d'hier avec statut "veille" OU "deja vendu"
    // (hier soir "j ai deja vendu" = ventes d'hier aussi)
    var estHierDirect = (date===yesterday);

    if (estAujourdHuiVeille || estHierDirect) {
      ventes+=parseInt(r[R_VENTES])||0;
      xtra  +=parseInt(r[R_XTRA])  ||0;
      choco +=parseInt(r[R_CHOCO]) ||0;
      van   +=parseInt(r[R_VAN])   ||0;
      count++;
    }
  });

  return {
    date:yesterday, nb_declarations:count,
    ventes_total:ventes, fanxtra_total:xtra,
    fanchoco_total:choco, fanvan_total:van,
  };
}


// ============================================================
//  DEPOTS MTD — CA réel (seulement "J ai deja vendu")
// ============================================================
function buildDepots(rows) {
  var m={};
  rows.forEach(function(r){
    var dep =String(r[R_DEPOT] ||"").trim();
    var stat=String(r[R_STATUT]||"").trim();
    if(!dep) return;
    if(!m[dep]) m[dep]={nom:dep,declarations:0,vendors:new Set(),ventes:0,fx:0,fc:0,fv:0};
    m[dep].declarations++;
    var ph=String(r[R_PHONE]||"").trim(); if(ph) m[dep].vendors.add(ph);
    if(isVenteAujourdHui(stat)){
      m[dep].ventes+=parseInt(r[R_VENTES])||0;
      m[dep].fx    +=parseInt(r[R_XTRA])  ||0;
      m[dep].fc    +=parseInt(r[R_CHOCO]) ||0;
      m[dep].fv    +=parseInt(r[R_VAN])   ||0;
    }
  });
  return Object.values(m).map(function(d){
    return{nom:d.nom,declarations:d.declarations,nb_vendors:d.vendors.size,
      ventes:d.ventes,fanxtra:d.fx,fanchoco:d.fc,fanvan:d.fv,pieces:d.fx+d.fc+d.fv};
  }).sort(function(a,b){return b.ventes-a.ventes;});
}


// ============================================================
//  DEPOT PAR JOUR (today ou yesterday)
// ============================================================
function buildDepotByDay(rows, today, which) {
  var yesterday = getYesterday(today);
  var m={};

  rows.forEach(function(r){
    var date=String(r[R_DATE]||"").trim();
    var stat=String(r[R_STATUT]||"").trim();
    var dep =String(r[R_DEPOT]||"").trim();
    if(!dep) return;

    var inclure = false;
    if(which==="today"){
      // Ventes d'aujourd'hui = lignes du jour avec "J ai deja vendu"
      inclure = (date===today && isVenteAujourdHui(stat));
    } else {
      // Ventes d'hier = lignes du jour avec "Je vais vendre"/"Non"
      //              + toutes les lignes d'hier
      inclure = (date===today && isVenteHier(stat)) || (date===yesterday);
    }
    if(!inclure) return;

    if(!m[dep]) m[dep]={nom:dep,declarations:0,vendors:new Set(),ventes:0,fx:0,fc:0,fv:0};
    m[dep].declarations++;
    var ph=String(r[R_PHONE]||"").trim(); if(ph) m[dep].vendors.add(ph);
    m[dep].ventes+=parseInt(r[R_VENTES])||0;
    m[dep].fx    +=parseInt(r[R_XTRA])  ||0;
    m[dep].fc    +=parseInt(r[R_CHOCO]) ||0;
    m[dep].fv    +=parseInt(r[R_VAN])   ||0;
  });

  return Object.values(m).map(function(d){
    return{nom:d.nom,declarations:d.declarations,nb_vendors:d.vendors.size,
      ventes:d.ventes,fanxtra:d.fx,fanchoco:d.fc,fanvan:d.fv,pieces:d.fx+d.fc+d.fv};
  }).sort(function(a,b){return b.ventes-a.ventes;});
}


// ============================================================
//  WEEKLY QPVD — basé sur "J ai deja vendu" uniquement
// ============================================================
function buildWeekly(rows) {
  var bySem={};
  rows.forEach(function(r){
    var ds  =String(r[R_DATE]||"").trim(); if(!ds) return;
    var stat=String(r[R_STATUT]||"").trim();
    var p=ds.split("/"); if(p.length<3) return;
    var d=new Date(parseInt(p[2]),parseInt(p[1])-1,parseInt(p[0]));
    var key=getWeekKey(d);
    if(!bySem[key]) bySem[key]={pieces:0,days:{},key:key};
    // Pièces = seulement ventes confirmées du jour
    if(isVenteAujourdHui(stat)){
      bySem[key].pieces+=(parseInt(r[R_XTRA])||0)+(parseInt(r[R_CHOCO])||0)+(parseInt(r[R_VAN])||0);
    }
    bySem[key].days[String(r[R_PHONE]||"")+"_"+ds]=true;
  });
  var keys=Object.keys(bySem).sort().slice(-7);
  return keys.map(function(k,i){
    var s=bySem[k],n=Object.keys(s.days).length;
    return{sem:"W"+(i+1),qpvd:n>0?Math.round(s.pieces/n):0,target:132};
  });
}
function getWeekKey(d){
  var j=new Date(d.getFullYear(),0,1);
  var w=Math.ceil(((d-j)/86400000+j.getDay()+1)/7);
  return d.getFullYear()+"-W"+(w<10?"0"+w:w);
}


// ============================================================
//  SATISFACTION — par vendor-day unique
// ============================================================
function buildSatisfaction(rows, today) {
  var p=today.split("/"),mois=parseInt(p[1]),annee=parseInt(p[2]);
  var parJourPhone={};
  rows.forEach(function(r){
    var dp=String(r[R_DATE]||"").split("/");
    if(dp.length<3||parseInt(dp[1])!==mois||parseInt(dp[2])!==annee) return;
    var ph=String(r[R_PHONE]||"").trim(); if(!ph) return;
    var key=dp[0]+"-"+ph;
    parJourPhone[key]={cat:String(r[R_CAT]||"").trim()};
  });
  var total=0,aucun=0;
  Object.values(parJourPhone).forEach(function(v){
    total++;
    if(v.cat==="Aucun probleme"||v.cat==="") aucun++;
  });
  return{rate:total>0?Math.round((aucun/total)*100):0,aucun_probleme:aucun,total_decla:total};
}


// ============================================================
//  EQUIPMENT
// ============================================================
function buildEquipment(rows, today) {
  var p=today.split("/"),mois=parseInt(p[1]),annee=parseInt(p[2]),issues=0;
  rows.forEach(function(r){
    if(String(r[R_CAT]||"").trim()!=="Probleme d equipement") return;
    var dp=String(r[R_DATE]||"").split("/");
    if(dp.length<3||parseInt(dp[1])!==mois||parseInt(dp[2])!==annee) return;
    issues++;
  });
  return{issues_mois:issues,jours_perdus:0,semaines:0,heures:0,
    statut:issues===0?"OK":"ALERTE"};
}


// ============================================================
//  PROBLEMS, PRIME, HOTSPOTS, MORNING/EVENING
// ============================================================
function buildProblems(rows,today){
  var p=today.split("/"),mois=parseInt(p[1]),annee=parseInt(p[2]),m={};
  rows.forEach(function(r){
    var cat=String(r[R_CAT]||"").trim();
    if(!cat||cat==="-"||cat==="Aucun probleme") return;
    var dp=String(r[R_DATE]||"").split("/");
    if(dp.length<3||parseInt(dp[1])!==mois||parseInt(dp[2])!==annee) return;
    m[cat]=(m[cat]||0)+1;
  });
  return Object.entries(m).map(function(e){return{categorie:e[0],count:e[1]};})
    .sort(function(a,b){return b.count-a.count;});
}
function buildPrime(rows){
  var m={};
  rows.forEach(function(r){
    var pr=String(r[R_PRIME]||"").trim(); if(!pr||pr==="-") return;
    m[pr]=(m[pr]||0)+1;
  });
  return Object.entries(m).map(function(e){return{pilier:e[0],count:e[1]};})
    .sort(function(a,b){return b.count-a.count;});
}
function buildHotspots(rows){
  var m={};
  rows.forEach(function(r){
    var lx=String(r[R_LIEU]||"").trim(); if(!lx||lx==="-") return;
    lx.split(",").forEach(function(l){l=l.trim();if(l)m[l]=(m[l]||0)+1;});
  });
  return Object.entries(m).map(function(e){return{lieu:e[0],count:e[1]};})
    .sort(function(a,b){return b.count-a.count;}).slice(0,10);
}
function buildMorningEvening(rows){
  var mt={declarations:0,ventes:0},so={declarations:0,ventes:0};
  rows.forEach(function(r){
    var per=String(r[R_PERIODE]||"").trim();
    var ca=parseInt(r[R_VENTES])||0;
    if(per==="Matin"){mt.declarations++;mt.ventes+=ca;}
    else{so.declarations++;so.ventes+=ca;}
  });
  return{
    morning:{declarations:mt.declarations,ventes:mt.ventes,
      avg:mt.declarations>0?Math.round(mt.ventes/mt.declarations):0},
    evening:{declarations:so.declarations,ventes:so.ventes,
      avg:so.declarations>0?Math.round(so.ventes/so.declarations):0},
  };
}


// ============================================================
//  RÉCONCILIATION Réponses → Vendors
// ============================================================
function reconcilierVendors(){
  try{
    var ss=SpreadsheetApp.openById(SHEET_ID);
    var sv=ss.getSheetByName(SHEET_VENDORS),sr=ss.getSheetByName(SHEET_REPONSES);
    if(!sv||!sr){Logger.log("Onglet introuvable");return;}
    var rv=sv.getDataRange().getValues(),ph={};
    for(var i=1;i<rv.length;i++){var p2=String(rv[i][V_PHONE]||"").trim();if(p2)ph[p2]=i+1;}
    var rr=sr.getDataRange().getValues(),last={};
    for(var j=1;j<rr.length;j++){
      var r=rr[j],p3=String(r[R_PHONE]||"").trim();if(!p3)continue;
      last[p3]={nom:String(r[R_NOM]||"").trim(),depot:String(r[R_DEPOT]||"").trim(),
        date:String(r[R_DATE]||"").trim(),ventes:parseInt(r[R_VENTES])||0,
        fx:parseInt(r[R_XTRA])||0,fc:parseInt(r[R_CHOCO])||0,fv:parseInt(r[R_VAN])||0};
    }
    var now=Utilities.formatDate(new Date(),TIMEZONE,"dd/MM/yyyy HH:mm"),a=0,m=0;
    Object.keys(last).forEach(function(p4){
      var info=last[p4];if(!info.nom||!info.depot)return;
      var pc=info.fx+info.fc+info.fv;
      if(!ph[p4]){sv.appendRow([p4,info.nom,info.depot,now,info.ventes,info.fx,info.fc,info.fv,pc,info.date]);a++;}
      else if(info.ventes>0||pc>0){sv.getRange(ph[p4],V_LAST_DEC+1,1,7).setValues([[now,info.ventes,info.fx,info.fc,info.fv,pc,info.date]]);m++;}
    });
    Logger.log("Synchro OK: "+a+" ajoutés, "+m+" mis à jour");
  }catch(e){Logger.log("Erreur: "+e.message);}
}

function onOpen(){
  try{
    SpreadsheetApp.getUi().createMenu("FanMilk Dashboard")
      .addItem("🔗 Tester l'API","testerAPI")
      .addItem("🔄 Synchro Vendors","reconcilierVendors")
      .addItem("⏰ Déclencheur 7h","installerDeclencheur")
      .addToUi();
  }catch(e){Logger.log("onOpen skipped: "+e.message);}
}

function testerAPI(){
  try{
    var d=buildData();
    SpreadsheetApp.getUi().alert(
      "✅ API OK\n\n"+
      "📅 Aujourd'hui : "+d.today_date+"\n"+
      "👥 Vendors uniques aujourd'hui : "+d.today.vendors_uniques+"\n"+
      "💬 Interactions totales : "+d.today.nb_declarations+"\n"+
      "✅ Déjà vendu aujourd'hui : "+d.today.vendors_qui_vendent+" vendors\n"+
      "💰 Ventes AUJOURD'HUI : "+d.today.ventes_total+" FCFA\n"+
      "📦 Ventes HIER (reportées) : "+d.yesterday.ventes_total+" FCFA\n"+
      "⭐ Satisfaction : "+d.satisfaction.rate+"%\n\n"+
      "🔗 https://fanmilk-dashboard.vercel.app/"
    );
  }catch(e){SpreadsheetApp.getUi().alert("Erreur: "+e.message);}
}

function installerDeclencheur(){
  ScriptApp.getProjectTriggers().forEach(function(t){
    if(t.getHandlerFunction()==="reconcilierVendors")ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("reconcilierVendors").timeBased().everyDays(1).atHour(7).create();
  SpreadsheetApp.getUi().alert("✅ Déclencheur installé à 7h chaque jour");
}
