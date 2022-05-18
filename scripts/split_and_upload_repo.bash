MAXFILESIZE=100000
MAXFILECOUNT=824
CONCURRENCY=64 #$((MAXFILECOUNT))

# unpack all packfiles
mv objects/pack/* . 2>/dev/null &&
for pack in *.pack; do
	git unpack-objects < "$pack" && rm -vf "$pack" "${pack%.pack}".idx
done

if [ "x$WALLET" != "x" ]
then
	WALLET="--wallet=$WALLET"
fi
if [ "x$GATEWAY" != "x" ]
then
	GATEWAY="--gateway=$GATEWAY"
fi
if [ "x$DEBUG" != "x" ]
then
	DEBUG="--debug"
fi

# make small object stores, can use dirsplit
prefix="$(date --iso=seconds)"
mkdir -p arweave
if ! cd arweave ; then exit -1; fi
rm -rf alt-*
if ! dirsplit -L --accuracy 1 --prefix "alt-$prefix-" --blksize $((MAXFILESIZE)) --size=$(((MAXFILECOUNT-1) * MAXFILESIZE)) ../objects
then
	exit -1
fi
cd ..

# upload each dir, accumulating the upload into an alternates file
LONGEST_TXID=43
ALTERNATES_DEPTH=0 # it is not actually a tree, as i am confused.
touch arweave/alternates-$ALTERNATES_DEPTH
for dir in arweave/alt-${prefix}-*
do
	NEXT_SIZE=$((LONGEST_TXID + 1))
	for alternates_file in arweave/alternates-*
	do
		NEXT_SIZE=$((NEXT_SIZE + $(stat -c %s "$alternates_file")))
	done
	if ((NEXT_SIZE >= MAXFILESIZE))
	then
		cat arweave/alternates-* > "$dir"/info/alternates
		sed 's!^\.\./\.\.!../arweave!' arweave/alternates-* > objects/info/alternates
		rm arweave/alternates-*
		touch arweave/alternates-0
		ALTERNATES_DEPTH=1
	fi
	if ! [ -d "$dir/objects" ]
	then
		if ! echo "$dir"/* | {
			mkdir "$dir"/objects
			xargs mv -v --target-directory="$dir/objects"
		}; then exit -1; fi
	fi
	echo git-object-store > "$dir"/git-object-store
	while true
	do
		if ! arkb deploy "$dir" $GATEWAY $WALLET $DEBUG --index git-object-store -v --no-colors --concurrency "$CONCURRENCY" --auto-confirm --use-bundler https://node2.bundlr.network --tag-name Type --tag-value git-object-store | tee "$dir".arkb.log; then exit -1; fi
		if ! grep "timeout of 100000ms exceeded" "$dir".arkb.log
		then
			break
		fi
	done
	txid="$(tail -n 1 "$dir".arkb.log | cut -d '/' -f 4)"
	TXID_LEN=$(($(echo -n "$txid" | wc -c)))
	if (( TXID_LEN != LONGEST_TXID ))
	then
		exit -1
	fi
	echo "Waiting for $txid to appear on arweave.net ..."
	while ! curl --fail --location https://arweave.net/"$txid"; do true; done
	echo "Success."
	if ! mv "$dir" arweave/"$txid"; then exit -1; fi
	rm -rf "$dir"
	rm arweave/"$txid"/*/*/manifest.arkb
	echo "../../$txid/objects" >> arweave/alternates-$((ALTERNATES_DEPTH))
	{ cd arweave/$txid/; find -type f; } | xargs rm -vrf
	sed 's!^\.\./\.\.!../arweave!' arweave/alternates-$((ALTERNATES_DEPTH)) > objects/info/alternates
	ALTERNATES_DEPTH=0
done

sed 's!^\.\./\.\.!../arweave!' arweave/alternates-* > objects/info/alternates

rm -rf arweave/git-dir 2>/dev/null
mkdir arweave/git-dir
cp -va description config info refs HEAD packed-refs objects   arweave/git-dir/
cat arweave/alternates-* > arweave/git-dir/objects/info/alternates
{ cd arweave/git-dir; git update-server-info; }

if ! arkb deploy arweave/git-dir $DEBUG $GATEWAY $WALLET -v --index HEAD --concurrency "$CONCURRENCY" --auto-confirm --use-bundler https://node2.bundlr.network --timeout $((60*60*1000)) --tag-name Type --tag-value git-dir | tee arweave/git-dir-$(date --iso=seconds).arkb.log; then exit -1; fi
rm -rf git-dir
