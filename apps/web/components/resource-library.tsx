const resources = [
  { agency: "FEMA", title: "Ready.gov disaster planning", description: "Build a household plan, emergency kit, and communication strategy.", url: "https://www.ready.gov/" },
  { agency: "NOAA / NWS", title: "Weather safety guides", description: "Official safety guidance for floods, tornadoes, heat, lightning, and more.", url: "https://www.weather.gov/safety/" },
  { agency: "American Red Cross", title: "Emergency preparedness", description: "Practical checklists organized by disaster type and recovery stage.", url: "https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies.html" },
  { agency: "USGS", title: "Earthquake hazards", description: "Authoritative earthquake information, maps, science, and preparedness links.", url: "https://www.usgs.gov/programs/earthquake-hazards" },
  { agency: "FEMA", title: "Flood preparedness", description: "Actions to take before, during, and after a flood.", url: "https://www.ready.gov/floods" },
  { agency: "FEMA", title: "Wildfire preparedness", description: "Evacuation, property, air quality, and recovery guidance.", url: "https://www.ready.gov/wildfires" },
];

export function ResourceLibrary() {
  return <main className="page-shell subpage"><div className="page-heading"><span className="eyebrow">Act on trusted guidance</span><h1>Natural disaster resources</h1><p>Official preparedness and safety information. In an immediate emergency, contact local emergency services and follow local alerts.</p></div><div className="resource-grid">{resources.map((resource) => <a href={resource.url} target="_blank" rel="noreferrer" key={resource.title}><span>{resource.agency}</span><h2>{resource.title}</h2><p>{resource.description}</p><strong>Open official resource ↗</strong></a>)}</div></main>;
}
