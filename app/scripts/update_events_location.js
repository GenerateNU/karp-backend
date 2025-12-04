// MongoDB script to update all events without valid locations
// with the location: 360 Huntington Ave, Boston, MA 02115
//
// Coordinates: [-71.0852898, 42.3376775] (longitude, latitude)
//
// Usage in MongoDB shell:
//   use your_database_name
//   load('app/scripts/update_events_location.js')
//   updateEventsWithoutLocation()

function updateEventsWithoutLocation() {
  const targetLocation = {
    type: "Point",
    coordinates: [-71.08681349999999, 42.3392591]  // [longitude, latitude] for 360 Huntington Ave, Boston, MA 02115
  };

  // Find events without valid location
  const query = {
    $or: [
      { location: { $exists: false } },
      { location: null },
      { "location.coordinates": { $exists: false } },
      { "location.coordinates": null },
      { "location.coordinates": { $size: { $ne: 2 } } }
    ]
  };

  // Update all matching events
  const result = db.events.updateMany(
    query,
    {
      $set: {
        location: targetLocation,
        address: "360 Huntington Ave, Boston, MA 02115"
      }
    }
  );

  print(`Updated ${result.modifiedCount} events with location: 360 Huntington Ave, Boston, MA 02115`);
  print(`Matched ${result.matchedCount} events total`);
  
  return result;
}

// Run the update
updateEventsWithoutLocation();

